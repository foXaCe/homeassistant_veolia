"""Sensor platform for Veolia."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CURRENCY_EURO, UnitOfVolume
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import LOGGER
from .entity import VeoliaEntity, VeoliaMesurements
from .statistics import import_volume_statistics


async def async_setup_entry(hass, entry, async_add_devices) -> None:
    """Set up sensor platform."""
    LOGGER.debug("Setting up sensor platform")
    coordinator = entry.runtime_data
    sensors = [
        LastIndexSensor(coordinator, entry),
        DailyConsumption(coordinator, entry),
        MonthlyConsumption(coordinator, entry),
        AnnualConsumption(coordinator, entry),
        LastDateSensor(coordinator, entry),
        BalanceSensor(coordinator, entry),
        MonthlyPaymentSensor(coordinator, entry),
        NextPaymentSensor(coordinator, entry),
        BillingIndexSensor(coordinator, entry),
    ]
    async_add_devices(sensors)


class LastIndexSensor(VeoliaMesurements):
    """LastIndexSensor sensor."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_last_index"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "veolia_index"

    @property
    def native_value(self) -> float | None:
        """Return sensor value."""
        value = self.coordinator.data.computed.last_index_m3
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state."""
        comp = self.coordinator.data.computed
        return {
            "data_type": comp.daily_fiability,
            "last_report": comp.last_date.isoformat() if comp.last_date else None,
        }

    @property
    def state_class(self) -> str:
        """Return the state_class of the sensor."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return UnitOfVolume.CUBIC_METERS

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 3

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:counter"

    async def async_added_to_hass(self) -> None:
        """Import historical meter-index statistics on add."""
        await super().async_added_to_hass()
        import_volume_statistics(
            self.hass,
            self.entity_id,
            self.coordinator.data.computed.index_stats_m3,
            UnitOfVolume.CUBIC_METERS,
        )


class DailyConsumption(VeoliaMesurements):
    """DailyConsumption sensor."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_daily_consumption"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "daily_consumption"

    @property
    def native_value(self) -> int | None:
        """Return sensor value (last available day, Veolia lags ~1 day)."""
        value = self.coordinator.data.computed.last_daily_liters
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state."""
        comp = self.coordinator.data.computed
        return {
            "data_type": comp.daily_fiability,
            "reading_date": comp.last_date.isoformat() if comp.last_date else None,
            "today": comp.daily_today_liters,
        }

    async def async_added_to_hass(self) -> None:
        """Import historical daily-consumption statistics on add."""
        await super().async_added_to_hass()
        import_volume_statistics(
            self.hass,
            self.entity_id,
            self.coordinator.data.computed.daily_stats_liters,
            UnitOfVolume.LITERS,
        )

    @property
    def state_class(self) -> str:
        """Return the state_class of the sensor."""
        return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return UnitOfVolume.LITERS

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 0

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:water"


class MonthlyConsumption(VeoliaMesurements):
    """MonthlyConsumption sensor."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_monthly_consumption"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "monthly_consumption"

    @property
    def native_value(self) -> float | None:
        """Return sensor value."""
        value = self.coordinator.data.computed.monthly_latest_m3
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state."""
        return {"data_type": self.coordinator.data.computed.monthly_fiability}

    @property
    def state_class(self) -> str:
        """Return the state_class of the sensor."""
        return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return UnitOfVolume.CUBIC_METERS

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 3

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:water"

    async def async_added_to_hass(self) -> None:
        """Import historical monthly-consumption statistics on add."""
        await super().async_added_to_hass()
        import_volume_statistics(
            self.hass,
            self.entity_id,
            self.coordinator.data.computed.monthly_stats_cubic_meters,
            UnitOfVolume.CUBIC_METERS,
        )


class AnnualConsumption(VeoliaMesurements):
    """AnnualConsumption sensor."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_annual_consumption"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "annual_consumption"

    @property
    def native_value(self) -> float | None:
        """Return sensor value."""
        value = self.coordinator.data.computed.annual_total_m3
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def state_class(self) -> str:
        """Return the state_class of the sensor."""
        return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return UnitOfVolume.CUBIC_METERS

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 3

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:water"


class LastDateSensor(CoordinatorEntity, SensorEntity):
    """LastDateSensor sensor."""

    def __init__(self, coordinator, config_entry) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_last_date"

    @property
    def has_entity_name(self) -> bool:
        """Indicate that entity has name defined."""
        return True

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "last_consumption_date"

    @property
    def native_value(self) -> str | None:
        """Return sensor value."""
        value = self.coordinator.data.computed.last_date
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:calendar"


class BalanceSensor(VeoliaEntity):
    """Account balance sensor (solde)."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_balance"

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "balance"

    @property
    def native_value(self) -> float | None:
        """Return sensor value."""
        value = self.coordinator.data.computed.balance
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def device_class(self) -> str:
        """Return the device_class of the sensor."""
        return SensorDeviceClass.MONETARY

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return CURRENCY_EURO

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 2

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:cash"


class MonthlyPaymentSensor(VeoliaEntity):
    """Monthly direct debit amount sensor (mensualité)."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_monthly_payment"

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "monthly_payment"

    @property
    def native_value(self) -> float | None:
        """Return sensor value."""
        value = self.coordinator.data.computed.monthly_payment
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value

    @property
    def device_class(self) -> str:
        """Return the device_class of the sensor."""
        return SensorDeviceClass.MONETARY

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return CURRENCY_EURO

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 2

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:cash-clock"


class NextPaymentSensor(VeoliaEntity):
    """Next scheduled direct debit sensor (prochain prélèvement)."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_next_payment"

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "next_payment"

    @property
    def native_value(self) -> str | None:
        """Return the next direct debit date, formatted for display (DD/MM/YYYY).

        A ``device_class: date`` sensor is rendered as raw ISO by the frontend,
        so we expose a locale-friendly string here and keep the ISO date in the
        ``date`` attribute for automations.
        """
        value = self.coordinator.data.computed.next_payment_date
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, value)
        return value.strftime("%d/%m/%Y") if value else None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state."""
        comp = self.coordinator.data.computed
        return {
            "date": comp.next_payment_date.isoformat()
            if comp.next_payment_date
            else None,
            "amount": comp.next_payment_amount,
        }

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:calendar-clock"


class BillingIndexSensor(VeoliaMesurements):
    """Official billing meter index sensor (index de facturation)."""

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_billing_index"

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""
        return "billing_index"

    @property
    def native_value(self) -> float | None:
        """Return sensor value (last official meter index)."""
        raw = self.coordinator.data.dernier_index_releve
        LOGGER.debug("Sensor %s value : %s", self.__class__.__name__, raw)
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def state_class(self) -> str:
        """Return the state_class of the sensor."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit_of_measurement of the sensor."""
        return UnitOfVolume.CUBIC_METERS

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision."""
        return 0

    @property
    def icon(self) -> str | None:
        """Set icon."""
        return "mdi:counter"

    @property
    def extra_state_attributes(self) -> dict:
        """Return contract information as attributes."""
        data = self.coordinator.data
        return {
            "reading_date": data.date_index_releve,
            "meter_number": data.numero_compteur,
            "reading_mode": data.mode_releve,
            "payment_mode": data.mode_paiement,
            "contract": data.libelle_contrat,
            "branch_address": data.adresse_de_branchement,
            "meter_location": data.emplacement_compteur,
            "status": data.statut,
            "customer_number": data.numero_client,
            "holder": data.titulaire,
            "brand": data.marque,
        }
