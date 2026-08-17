"""Raw-TCP client and state parser for the MT-VIKI matrix."""

from __future__ import annotations

import asyncio
import logging
import re

from .const import (
    CONNECT_TIMEOUT,
    LINE_TERMINATOR,
    QUERY_COMMANDS,
    READ_TIMEOUT,
    SWITCH_COMMAND,
)

_LOGGER = logging.getLogger(__name__)


class MatrixError(Exception):
    """Raised when communication with the matrix fails."""


def parse_state_response(
    text: str, outputs: int, inputs: int
) -> dict[int, int] | None:
    """Parse a raw device reply into a ``{output: input}`` routing map.

    The read command for these units is undocumented, so this scans for a few
    plausible response shapes rather than assuming one exact format:

    * ``SWS 1 2 3 4 5 1 7 8`` — the device's own status line (also returned as the
      reply to a ``SW`` switch command); ``SWS`` followed by one input number per
      output, in order. This is the confirmed format for the MT-VIKI HD0808.
    * ``OUT01 IN03`` / ``O1 I3`` (labelled pairs, any separator/zero-padding)
    * ``Output 1: Input 3`` / ``Out 1 -> 3`` (labelled, word forms)
    * a bare compact table of one input digit per output, e.g. ``31245678``

    Returns a dict mapping every output (1..``outputs``) to an input
    (1..``inputs``), or ``None`` if nothing parseable/complete was found. Callers
    treat ``None`` as "device didn't answer with usable state".
    """
    if not text:
        return None

    # Shape 0: the device's native ``SWS`` status line. Take the run of numbers
    # after the ``SWS`` token, positionally: value N is the input feeding output N.
    for line in text.splitlines():
        match = re.search(r"SWS[\s:]*([\d\s]+)", line, re.IGNORECASE)
        if not match:
            continue
        numbers = [int(n) for n in match.group(1).split()]
        if len(numbers) == outputs and all(1 <= n <= inputs for n in numbers):
            return {out: inp for out, inp in enumerate(numbers, start=1)}

    result: dict[int, int] = {}

    # Shapes 1 & 2: labelled pairs, one per line. On any line that mentions an
    # output ("out"/"output"), the first number is the output and the second is the
    # input routed to it. This covers "OUT01 IN03", "Output 1: Input 3",
    # "Out 1 -> 3", etc. without assuming a specific separator.
    for line in text.splitlines():
        if "out" not in line.lower():
            continue
        numbers = re.findall(r"\d+", line)
        if len(numbers) < 2:
            continue
        out, inp = int(numbers[0]), int(numbers[1])
        if 1 <= out <= outputs and 1 <= inp <= inputs:
            result.setdefault(out, inp)

    if len(result) == outputs:
        return result

    # Shape 3: a bare compact table — exactly ``outputs`` digits in a row, each a
    # valid input number, position N giving the input routed to output N.
    for line in text.splitlines():
        digits = re.sub(r"\D", "", line)
        if len(digits) == outputs and all(
            1 <= int(d) <= inputs for d in digits
        ):
            return {out: int(d) for out, d in enumerate(digits, start=1)}

    return result or None


class MatrixClient:
    """Minimal async client for the MT-VIKI matrix over raw TCP.

    A short-lived connection is opened per operation. These devices typically
    accept only one connection at a time, so holding a socket open would block
    the front panel and other controllers.
    """

    def __init__(self, host: str, port: int, outputs: int, inputs: int) -> None:
        """Initialise the client for ``host``:``port``."""
        self._host = host
        self._port = port
        self._outputs = outputs
        self._inputs = inputs
        self._lock = asyncio.Lock()
        # Once a query command yields a parseable reply, prefer it on later polls.
        self._working_query: str | None = None
        # None = untried, True = a query works, False = none do (stop probing).
        self._query_supported: bool | None = None

    async def _send(self, command: str, read_reply: bool) -> str:
        """Open a connection, send ``command`` + terminator, optionally read a reply."""
        async with self._lock:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=CONNECT_TIMEOUT,
                )
            except (OSError, asyncio.TimeoutError) as err:
                raise MatrixError(
                    f"Cannot connect to {self._host}:{self._port}: {err}"
                ) from err

            try:
                writer.write((command + LINE_TERMINATOR).encode("ascii"))
                await writer.drain()

                if not read_reply:
                    return ""

                # Read whatever the device sends within the window. The reply length
                # is unknown, so drain until EOF or the read times out.
                chunks: list[bytes] = []
                try:
                    while True:
                        data = await asyncio.wait_for(
                            reader.read(1024), timeout=READ_TIMEOUT
                        )
                        if not data:
                            break
                        chunks.append(data)
                except asyncio.TimeoutError:
                    pass
                return b"".join(chunks).decode("ascii", errors="ignore")
            finally:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=CONNECT_TIMEOUT)
                except (OSError, asyncio.TimeoutError):
                    pass

    async def async_switch(
        self, input_ch: int, output_ch: int
    ) -> dict[int, int] | None:
        """Route ``input_ch`` to ``output_ch``.

        The matrix replies with its full ``SWS`` status line, so this returns the
        complete parsed routing map when available — letting the caller sync every
        output at once, not just the one it changed.
        """
        command = SWITCH_COMMAND.format(input=input_ch, output=output_ch)
        reply = await self._send(command, read_reply=True)
        _LOGGER.debug("Switch %s reply: %r", command, reply)
        if "ERR" in reply.upper():
            raise MatrixError(f"Matrix rejected command {command!r}: {reply!r}")
        return parse_state_response(reply, self._outputs, self._inputs)

    async def async_query_state(self) -> dict[int, int] | None:
        """Best-effort read of the current routing map.

        Tries each candidate query command until one yields a parseable reply, and
        remembers the winner for next time. If a full probe finds nothing usable,
        it stops probing on later calls (returning ``None`` immediately) so polls
        stay fast and the caller can rely on optimistically-tracked state instead.
        """
        # A previous full probe found no working query: don't keep hammering the
        # device with commands it ignores every poll.
        if self._query_supported is False:
            return None

        # Prefer a command already known to work, then the rest.
        candidates = QUERY_COMMANDS
        if self._working_query:
            candidates = [self._working_query] + [
                c for c in QUERY_COMMANDS if c != self._working_query
            ]

        for command in candidates:
            reply = await self._send(command, read_reply=True)
            _LOGGER.debug("Query %r raw reply: %r", command, reply)
            parsed = parse_state_response(reply, self._outputs, self._inputs)
            if parsed:
                self._working_query = command
                self._query_supported = True
                return parsed

        self._query_supported = False
        _LOGGER.info(
            "No status-query command worked; HA will sync from switch replies "
            "instead. Enable debug logging to capture the device's replies."
        )
        return None

    async def async_test_connection(self) -> None:
        """Open and close a connection to verify the host is reachable."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=CONNECT_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError) as err:
            raise MatrixError(
                f"Cannot connect to {self._host}:{self._port}: {err}"
            ) from err
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=CONNECT_TIMEOUT)
        except (OSError, asyncio.TimeoutError):
            pass
