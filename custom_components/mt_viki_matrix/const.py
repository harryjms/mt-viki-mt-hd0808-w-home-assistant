"""Constants for the MT-VIKI matrix integration."""

from __future__ import annotations

DOMAIN = "mt_viki_matrix"

# Matrix geometry. The HD-414 / HD0808 is 8x8. These are kept as constants so the
# integration can be retargeted at a 4x4 or 16x16 unit by changing them in one place.
INPUTS = 8
OUTPUTS = 8

# Connection defaults. These units are driven over a raw TCP socket.
DEFAULT_PORT = 8080
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 2.0

# Config-entry keys.
CONF_HOST = "host"
CONF_PORT = "port"

# Options keys.
CONF_INPUT_NAMES = "input_names"
CONF_OUTPUT_NAMES = "output_names"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30  # seconds

# Protocol. Commands are plain text terminated by CRLF; the device replies "OK"/"ERR".
LINE_TERMINATOR = "\r\n"
# Switch input -> output. Formatted as: SW <input> <output>
SWITCH_COMMAND = "SW {input} {output}"

# The read/query-state command is undocumented for these units. We send a best-guess
# query and parse the reply (see matrix.parse_state_response). Candidates are tried in
# order until one yields a parseable reply; the probe then stops (see async_query_state).
# The device answers a switch with an "SWS <per-output input>" status line, so the query
# most likely to elicit the same line is a bare "SWS"/"SW" or a period-terminated status
# verb (the RS232 manual notes commands end with "."). Kept here so they are trivial to
# adjust once a real device response is captured (enable DEBUG logging to see it).
QUERY_COMMANDS = ["SWS", "SW", "STATUS.", "Status.", "STA.", "READ."]
