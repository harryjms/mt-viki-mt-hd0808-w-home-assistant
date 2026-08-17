"""Output select entities for the MT-VIKI matrix.

One select per output. Its options are the inputs, each labelled with the input
number and the input entity's name as shown in Home Assistant (e.g. ``3: Apple TV``),
so renaming an input entity updates the dropdowns. Selecting an option routes that
input to the output.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INPUTS, OUTPUTS
from .coordinator import MtVikiCoordinator
from .helpers import input_option_label, output_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the output select entities."""
    coordinator: MtVikiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MatrixOutputSelect(coordinator, entry, output_ch)
        for output_ch in range(1, OUTPUTS + 1)
    )


class MatrixOutputSelect(CoordinatorEntity[MtVikiCoordinator], SelectEntity):
    """Represents one matrix output and the input routed to it."""

    _attr_icon = "mdi:hdmi-port"
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: MtVikiCoordinator,
        entry: ConfigEntry,
        output_ch: int,
    ) -> None:
        """Initialise the output select."""
        super().__init__(coordinator)
        self._entry = entry
        self._output = output_ch
        self._attr_unique_id = f"{entry.entry_id}_out_{output_ch}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="MT-VIKI",
            model="HD-414 / HD0808 8x8 Matrix",
        )

    @property
    def name(self) -> str:
        """Configured output name."""
        return output_name(self._entry, self._output)

    @property
    def options(self) -> list[str]:
        """Input labels, one per input: ``<number>: <input entity name>``."""
        return [
            input_option_label(self.hass, self._entry, i)
            for i in range(1, INPUTS + 1)
        ]

    @property
    def current_option(self) -> str | None:
        """Label of the input currently routed to this output, if known."""
        input_ch = (self.coordinator.data or {}).get(self._output)
        if input_ch is None:
            return None
        return input_option_label(self.hass, self._entry, input_ch)

    async def async_select_option(self, option: str) -> None:
        """Route the chosen input to this output."""
        # Labels are ``<number>: <name>`` — the input number is the leading token.
        input_ch = int(option.split(":", 1)[0])
        await self.coordinator.async_set_route(self._output, input_ch)
