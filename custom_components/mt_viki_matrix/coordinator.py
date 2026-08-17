"""Data update coordinator for the MT-VIKI matrix."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .matrix import MatrixClient, MatrixError

_LOGGER = logging.getLogger(__name__)


class MtVikiCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Poll the matrix for state and hold optimistic routing between polls."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MatrixClient,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, int]:
        """Fetch current routing, preserving optimistic state when unreadable.

        The read command is undocumented, so ``async_query_state`` may return
        ``None`` even when the device is perfectly reachable. In that case we keep
        the last known map (optimistic tracking) rather than wiping every entity.
        """
        try:
            state = await self.client.async_query_state()
        except MatrixError as err:
            raise UpdateFailed(str(err)) from err

        if state:
            return state
        # Device reachable but gave no parseable state: hold what we have.
        return self.data or {}

    async def async_set_route(self, output_ch: int, input_ch: int) -> None:
        """Switch ``input_ch`` to ``output_ch`` and update state from the reply.

        The matrix answers a switch with its full ``SWS`` status line, so when that
        parses we adopt the complete real map (syncing every output at once). If it
        doesn't parse, we fall back to an optimistic single-output update.
        """
        full_state = await self.client.async_switch(input_ch, output_ch)
        if full_state:
            self.async_set_updated_data(full_state)
            return
        new_state = dict(self.data or {})
        new_state[output_ch] = input_ch
        self.async_set_updated_data(new_state)
