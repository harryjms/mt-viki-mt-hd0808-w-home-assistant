"""Shared helpers for reading configured input/output names."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .const import CONF_INPUT_NAMES, CONF_OUTPUT_NAMES, INPUTS, OUTPUTS


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


def input_option_label(entry: ConfigEntry, channel: int) -> str:
    """Dropdown label for an input: its number and configured name, e.g. ``3: Apple TV``."""
    return f"{channel}: {input_name(entry, channel)}"
