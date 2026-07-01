"""DataUpdateCoordinator for the HASmarterMeter integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from calendar import monthrange

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_READINGS_PATH,
    API_TARIFFS_PATH,
    CONF_API_KEY,
    CONF_HOST,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    READINGS_COUNT,
    SUCCESS_RATE_WINDOW,
)

_LOGGER = logging.getLogger(__name__)


class SmarterMeterData:
    """Holds the processed SmarterMeter data exposed to sensor entities."""

    def __init__(
        self,
        current_reading: float | None,
        usage_24h: float | None,
        cost_24h: float | None,
        usage_7d: float | None,
        cost_7d: float | None,
        usage_30d: float | None,
        cost_30d: float | None,
        success_rate: float | None,
    ) -> None:
        """Initialise SmarterMeterData."""
        self.current_reading = current_reading
        self.usage_24h = usage_24h
        self.cost_24h = cost_24h
        self.usage_7d = usage_7d
        self.cost_7d = cost_7d
        self.usage_30d = usage_30d
        self.cost_30d = cost_30d
        self.success_rate = success_rate


class SmarterMeterCoordinator(DataUpdateCoordinator[SmarterMeterData]):
    """Polls the SmarterMeter API and computes usage and cost for each period."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator with host and API key from the config entry."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )

        self.Host: str = entry.data[CONF_HOST].rstrip("/")
        self.ApiKey: str = entry.data[CONF_API_KEY]
        self.Session: aiohttp.ClientSession = async_get_clientsession(hass)

    async def _async_update_data(self) -> SmarterMeterData:
        """Fetch readings and tariffs, then compute all sensor values."""
        headers = {"X-Api-Key": self.ApiKey}

        try:
            async with self.Session.get(
                f"{self.Host}{API_READINGS_PATH}?count={READINGS_COUNT}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    raise UpdateFailed("SmarterMeter API rejected the configured API key")
                response.raise_for_status()
                readings: list[dict[str, Any]] = await response.json()

            async with self.Session.get(
                f"{self.Host}{API_TARIFFS_PATH}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                tariffs: list[dict[str, Any]] = await response.json()

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with SmarterMeter API: {err}") from err

        if not readings:
            return SmarterMeterData(None, None, None, None, None, None, None, None)

        readings.sort(key=lambda r: r["capturedAt"])

        now = datetime.now(timezone.utc)

        current_reading = float(readings[-1]["value"])

        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month = first_of_this_month - timedelta(days=1)
        days_in_prev_month = monthrange(prev_month.year, prev_month.month)[1]

        start_24h = now - timedelta(hours=24)
        start_7d = now - timedelta(days=7)
        start_30d = now - timedelta(days=days_in_prev_month)

        usage_24h = self._calculate_usage(readings, start_24h, now)
        usage_7d = self._calculate_usage(readings, start_7d, now)
        usage_30d = self._calculate_usage(readings, start_30d, now)

        cost_24h = self._calculate_cost(readings, tariffs, start_24h, now)
        cost_7d = self._calculate_cost(readings, tariffs, start_7d, now)
        cost_30d = self._calculate_cost(readings, tariffs, start_30d, now)

        success_rate = self._calculate_success_rate(readings, now)

        return SmarterMeterData(
            current_reading=current_reading,
            usage_24h=usage_24h,
            cost_24h=cost_24h,
            usage_7d=usage_7d,
            cost_7d=cost_7d,
            usage_30d=usage_30d,
            cost_30d=cost_30d,
            success_rate=success_rate,
        )

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        """Parse an ISO 8601 datetime string to a UTC-aware datetime."""
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _calculate_usage(
        self, readings: list[dict[str, Any]], start: datetime, end: datetime
    ) -> float | None:
        """Return kWh delta using the last reading before the window as the baseline."""
        window = [r for r in readings if start <= self._parse_dt(r["capturedAt"]) <= end]

        before = [r for r in readings if self._parse_dt(r["capturedAt"]) < start]

        if not window:
            return None

        last_value = float(window[-1]["value"])

        if before:
            first_value = float(before[-1]["value"])
        elif window:
            first_value = float(window[0]["value"])
        else:
            return None

        return round(max(0.0, last_value - first_value), 3)

    def _calculate_cost(
        self,
        readings: list[dict[str, Any]],
        tariffs: list[dict[str, Any]],
        range_start: datetime,
        range_end: datetime,
    ) -> float | None:
        """Calculate cost in £ clipping usage and standing charge per tariff period.

        Mirrors the C# CalculateCostForRange logic: for each tariff, clip its date
        range to the requested range, find readings within that clipped period,
        compute usage delta and standing charge days, then sum across all tariffs.
        """
        total_cost = 0.0
        any_tariff_matched = False

        for tariff in tariffs:
            tariff_start = self._parse_dt(tariff["startDate"] + "T00:00:00+00:00" if "T" not in tariff["startDate"] else tariff["startDate"])
            tariff_end = self._parse_dt(tariff["endDate"] + "T23:59:59+00:00" if "T" not in tariff["endDate"] else tariff["endDate"])

            period_start = max(range_start, tariff_start)
            period_end = min(range_end, tariff_end)

            if period_start > period_end:
                continue

            any_tariff_matched = True

            days = (period_end.date() - period_start.date()).days + 1

            period_readings = [
                r for r in readings
                if period_start <= self._parse_dt(r["capturedAt"]) <= period_end
            ]

            usage = 0.0
            if len(period_readings) >= 2:
                usage = max(0.0, float(period_readings[-1]["value"]) - float(period_readings[0]["value"]))

            total_cost += (usage * tariff["unitRatePence"] + days * tariff["standingChargePence"]) / 100

        if not any_tariff_matched:
            return None

        return round(total_cost, 2)

    def _calculate_success_rate(self, readings: list[dict[str, Any]], now: datetime) -> float:
        """Return success rate as a percentage based on readings in the last 200 hours."""
        window_start = now - timedelta(hours=SUCCESS_RATE_WINDOW * 2)
        recent = [
            r for r in readings
            if self._parse_dt(r["capturedAt"]) >= window_start
        ]
        return round(min(len(recent) / SUCCESS_RATE_WINDOW * 100, 100), 1)