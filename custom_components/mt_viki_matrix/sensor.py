"""Input sensor entities for the MT-VIKI matrix.

One read-only sensor per input. Its state is the number of outputs currently fed
by that input, with an attribute listing those output names.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INPUTS, OUTPUTS
from .coordinator import MtVikiCoordinator
from .helpers import input_name, output_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the input sensor entities."""
    coordinator: MtVikiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MatrixInputSensor(coordinator, entry, input_ch)
        for input_ch in range(1, INPUTS + 1)
    )


class MatrixInputSensor(CoordinatorEntity[MtVikiCoordinator], SensorEntity):
    """Represents one matrix input and which outputs it currently feeds."""

    _attr_icon = "mdi:import"
    _attr_native_unit_of_measurement = "outputs"

    def __init__(
        self,
        coordinator: MtVikiCoordinator,
        entry: ConfigEntry,
        input_ch: int,
    ) -> None:
        """Initialise the input sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._input = input_ch
        self._attr_unique_id = f"{entry.entry_id}_in_{input_ch}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="MT-VIKI",
            model="HD-414 / HD0808 8x8 Matrix",
        )

    @property
    def name(self) -> str:
        """Configured input name."""
        return input_name(self._entry, self._input)

    def _routed_outputs(self) -> list[int]:
        """Output channels currently fed by this input."""
        data = self.coordinator.data or {}
        return [out for out, inp in data.items() if inp == self._input]

    @property
    def native_value(self) -> int:
        """Number of outputs currently showing this input."""
        return len(self._routed_outputs())

    @property
    def extra_state_attributes(self) -> dict[str, list[str] | list[int]]:
        """Names and numbers of the outputs currently showing this input."""
        outs = sorted(self._routed_outputs())
        return {
            "input_number": self._input,
            "output_numbers": outs,
            "outputs": [output_name(self._entry, o) for o in outs],
        }
