"""DataUpdateCoordinator for the HASmarterMeter integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_SUMMARY_PATH,
    CONF_API_KEY,
    CONF_HOST,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
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
        last_captured_at: str | None,
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
        self.last_captured_at = last_captured_at
        self.success_rate = success_rate


class SmarterMeterCoordinator(DataUpdateCoordinator[SmarterMeterData]):
    """Polls the SmarterMeter summary endpoint and exposes results as sensor data."""

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
        """Fetch the summary from the API and return it as SmarterMeterData."""
        headers = {"X-Api-Key": self.ApiKey}

        try:
            async with self.Session.get(
                f"{self.Host}{API_SUMMARY_PATH}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    raise UpdateFailed("SmarterMeter API rejected the configured API key")
                response.raise_for_status()
                data: dict[str, Any] = await response.json()

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with SmarterMeter API: {err}") from err

        return SmarterMeterData(
            current_reading=data.get("currentReading"),
            usage_24h=data.get("todayUsage"),
            cost_24h=data.get("todayCost"),
            usage_7d=data.get("weekUsage"),
            cost_7d=data.get("weekCost"),
            usage_30d=data.get("monthUsage"),
            cost_30d=data.get("monthCost"),
            last_captured_at=data.get("lastCapturedAt"),
            success_rate=data.get("successRate"),
        )