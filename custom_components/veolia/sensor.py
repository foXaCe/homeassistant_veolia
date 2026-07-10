"""Sensor platform for Veolia."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CURRENCY_EURO, UnitOfVolume

from .entity import VeoliaBaseEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import VeoliaConfigEntry
    from .model import VeoliaModel

PARALLEL_UPDATES = 0


def _format_next_payment(data: VeoliaModel) -> str | None:
    """Format the next direct debit date for display (DD/MM/YYYY).

    A ``device_class: date`` sensor is rendered as raw ISO by the frontend,
    so a locale-friendly string is exposed here and the ISO date is kept in
    the ``date`` attribute for automations.
    """
    value = data.computed.next_payment_date
    return value.strftime("%d/%m/%Y") if value else None


def _billing_index(data: VeoliaModel) -> float | None:
    """Return the official billing meter index as a float."""
    try:
        raw = data.dernier_index_releve
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class VeoliaSensorEntityDescription(SensorEntityDescription):
    """Description of a Veolia sensor."""

    value_fn: Callable[[VeoliaModel], Any]
    attributes_fn: Callable[[VeoliaModel], dict[str, Any]] | None = None


SENSORS: tuple[VeoliaSensorEntityDescription, ...] = (
    VeoliaSensorEntityDescription(
        key="last_index",
        translation_key="veolia_index",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        value_fn=lambda data: data.computed.last_index_m3,
        attributes_fn=lambda data: {
            "data_type": data.computed.daily_fiability,
            "last_report": (
                data.computed.last_date.isoformat() if data.computed.last_date else None
            ),
        },
    ),
    VeoliaSensorEntityDescription(
        key="daily_consumption",
        translation_key="daily_consumption",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=0,
        value_fn=lambda data: data.computed.last_daily_liters,
        attributes_fn=lambda data: {
            "data_type": data.computed.daily_fiability,
            "reading_date": (
                data.computed.last_date.isoformat() if data.computed.last_date else None
            ),
            "today": data.computed.daily_today_liters,
        },
    ),
    VeoliaSensorEntityDescription(
        key="monthly_consumption",
        translation_key="monthly_consumption",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        value_fn=lambda data: data.computed.monthly_latest_m3,
        attributes_fn=lambda data: {"data_type": data.computed.monthly_fiability},
    ),
    VeoliaSensorEntityDescription(
        key="annual_consumption",
        translation_key="annual_consumption",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=3,
        value_fn=lambda data: data.computed.annual_total_m3,
    ),
    VeoliaSensorEntityDescription(
        key="last_date",
        translation_key="last_consumption_date",
        value_fn=lambda data: data.computed.last_date,
    ),
    VeoliaSensorEntityDescription(
        key="balance",
        translation_key="balance",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data: data.computed.balance,
    ),
    VeoliaSensorEntityDescription(
        key="monthly_payment",
        translation_key="monthly_payment",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data: data.computed.monthly_payment,
    ),
    VeoliaSensorEntityDescription(
        key="next_payment",
        translation_key="next_payment",
        value_fn=_format_next_payment,
        attributes_fn=lambda data: {
            "date": (
                data.computed.next_payment_date.isoformat()
                if data.computed.next_payment_date
                else None
            ),
            "amount": data.computed.next_payment_amount,
        },
    ),
    VeoliaSensorEntityDescription(
        key="billing_index",
        translation_key="billing_index",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=0,
        value_fn=_billing_index,
        attributes_fn=lambda data: {
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
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VeoliaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Veolia sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        VeoliaSensor(coordinator, description) for description in SENSORS
    )


class VeoliaSensor(VeoliaBaseEntity, SensorEntity):
    """Veolia sensor driven by its entity description."""

    entity_description: VeoliaSensorEntityDescription

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
