"""Sensor platform for HASmarterMeter."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmarterMeterCoordinator, SmarterMeterData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HASmarterMeter sensors from a config entry."""
    coordinator: SmarterMeterCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        CurrentReadingSensor(coordinator, entry),
        UsageSensor(coordinator, entry, "24h", "Last 24 Hours"),
        CostSensor(coordinator, entry, "24h", "Last 24 Hours"),
        UsageSensor(coordinator, entry, "7d", "Last 7 Days"),
        CostSensor(coordinator, entry, "7d", "Last 7 Days"),
        UsageSensor(coordinator, entry, "30d", "Last 30 Days"),
        CostSensor(coordinator, entry, "30d", "Last 30 Days"),
        SuccessRateSensor(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return shared device info for all HASmarterMeter sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="HASmarterMeter",
    )


class CurrentReadingSensor(CoordinatorEntity[SmarterMeterCoordinator], SensorEntity):
    """Reports the latest cumulative meter reading in kWh."""

    _attr_name = "Current Reading"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 0
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmarterMeterCoordinator, entry: ConfigEntry) -> None:
        """Initialise the current reading sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current_reading"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Return the latest meter reading."""
        data: SmarterMeterData = self.coordinator.data
        return data.current_reading if data else None


class UsageSensor(CoordinatorEntity[SmarterMeterCoordinator], SensorEntity):
    """Reports kWh usage for a given period."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmarterMeterCoordinator, entry: ConfigEntry, period_key: str, period_label: str) -> None:
        """Initialise the usage sensor for a given period."""
        super().__init__(coordinator)
        self.PeriodKey: str = period_key
        self._attr_name = f"Usage {period_label}"
        self._attr_unique_id = f"{entry.entry_id}_usage_{period_key}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Return the kWh usage for this period."""
        data: SmarterMeterData = self.coordinator.data
        if data is None:
            return None
        return getattr(data, f"usage_{self.PeriodKey}")


class CostSensor(CoordinatorEntity[SmarterMeterCoordinator], SensorEntity):
    """Reports electricity cost in £ for a given period."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "GBP"
    _attr_suggested_display_precision = 2
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmarterMeterCoordinator, entry: ConfigEntry, period_key: str, period_label: str) -> None:
        """Initialise the cost sensor for a given period."""
        super().__init__(coordinator)
        self.PeriodKey: str = period_key
        self._attr_name = f"Cost {period_label}"
        self._attr_unique_id = f"{entry.entry_id}_cost_{period_key}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Return the cost in £ for this period."""
        data: SmarterMeterData = self.coordinator.data
        if data is None:
            return None
        return getattr(data, f"cost_{self.PeriodKey}")


class SuccessRateSensor(CoordinatorEntity[SmarterMeterCoordinator], SensorEntity):
    """Reports the reading capture success rate as a percentage."""

    _attr_name = "Reading Success Rate"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_has_entity_name = True
    _attr_icon = "mdi:percent"

    def __init__(self, coordinator: SmarterMeterCoordinator, entry: ConfigEntry) -> None:
        """Initialise the success rate sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_success_rate"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Return the reading success rate as a percentage."""
        data: SmarterMeterData = self.coordinator.data
        return data.success_rate if data else None