"""Shared helpers for reading configured input/output names."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_INPUT_NAMES, CONF_OUTPUT_NAMES, DOMAIN, INPUTS, OUTPUTS


def default_input_names() -> list[str]:
    """Return the default input names (``Input 1`` .. ``Input N``)."""
    return [f"Input {i}" for i in range(1, INPUTS + 1)]


def default_output_names() -> list[str]:
    """Return the default output names (``Output 1`` .. ``Output N``)."""
    return [f"Output {i}" for i in range(1, OUTPUTS + 1)]


def _name(names: list[str], defaults: list[str], channel: int) -> str:
    """Return the configured name for a 1-based ``channel``, falling back to default."""
    idx = channel - 1
    if 0 <= idx < len(names) and names[idx]:
        return names[idx]
    return defaults[idx]


def input_name(entry: ConfigEntry, channel: int) -> str:
    """Configured display name for input ``channel`` (1-based)."""
    names = entry.options.get(CONF_INPUT_NAMES) or []
    return _name(names, default_input_names(), channel)


def output_name(entry: ConfigEntry, channel: int) -> str:
    """Configured display name for output ``channel`` (1-based)."""
    names = entry.options.get(CONF_OUTPUT_NAMES) or []
    return _name(names, default_output_names(), channel)


def input_display_name(
    hass: HomeAssistant, entry: ConfigEntry, channel: int
) -> str:
    """Display name for input ``channel``, honouring the user's HA entity rename.

    Prefers the input sensor entity's name as shown in Home Assistant (a custom
    rename in the entity registry, else its original name), so renaming the input
    entity in the UI also updates the output dropdowns. Falls back to the
    integration's configured/default input name if the entity isn't registered yet.
    """
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_in_{channel}"
    )
    if entity_id and (entity := registry.async_get(entity_id)):
        name = entity.name or entity.original_name
        if name:
            return name
    return input_name(entry, channel)


def input_option_label(
    hass: HomeAssistant, entry: ConfigEntry, channel: int
) -> str:
    """Dropdown label for an input: its number and display name, e.g. ``3: Apple TV``."""
    return f"{channel}: {input_display_name(hass, entry, channel)}"
