# MT-VIKI Matrix — Home Assistant integration

A custom [Home Assistant](https://www.home-assistant.io/) integration to control an
**MT-VIKI HD-414 / HD0808 8×8 HDMI/video matrix** over the network.

- One **select** entity per output — its dropdown lists every input as `«number»: «name»`
  (e.g. `3: Apple TV`), and choosing an option routes that input to the output.
- One **sensor** entity per input — shows how many outputs it currently feeds, with the
  output names as attributes.
- All 8 inputs and 8 outputs are **namable** from the integration's options.
- Home Assistant **polls the matrix** to stay in sync, and tracks routing **optimistically**
  between polls so the UI reacts instantly to changes you make from Home Assistant.

## Installation

### HACS (recommended)
Add this repository as a **custom repository** of type *Integration*, install
**MT-VIKI Matrix**, then restart Home Assistant.

1. In HACS, open the **⋮** menu → **Custom repositories**.
2. Repository: `https://github.com/harryjms/mt-viki-mt-hd0808-w-home-assistant` —
   Category: **Integration** → **Add**.
3. Search for and download **MT-VIKI Matrix**, then **restart Home Assistant**.

### Manual
Copy `custom_components/mt_viki_matrix` into your Home Assistant `config/custom_components/`
directory and restart.

## Configuration

1. **Settings → Devices & Services → Add Integration → “MT-VIKI Matrix”.**
2. Enter the matrix's **host / IP** and **TCP port** (default **8080**). Home Assistant
   verifies it can open a connection.
3. Open the integration's **Configure** dialog to **name each input and output** and set
   the **poll interval** (seconds).

You get eight output `select` entities and eight input `sensor` entities, all grouped under
one device. Renaming inputs/outputs updates the entities and the dropdown labels live.

## How it talks to the matrix

These units accept plain-text commands over a raw TCP socket. Switching sends:

```
SW <input> <output>\r\n
```

A short-lived connection is opened per command (the matrix generally allows only one
connection at a time, so Home Assistant never holds the socket open).

## Keeping in sync (and improving readback)

The matrix answers a switch (`SW <in> <out>`) with a full status line of the form
`SWS <in-for-out1> <in-for-out2> … <in-for-out8>`. The integration parses that line, so
**every switch made in Home Assistant instantly syncs all eight outputs** to the device's
real routing (see `parse_state_response` in `custom_components/mt_viki_matrix/matrix.py`).

For passive polling, the **read-only** status-query command is *not* publicly documented,
so the integration is deliberately resilient:

- On each poll it probes a short list of candidate query commands (`QUERY_COMMANDS` in
  `const.py`). If one returns a parseable `SWS` line, that command is remembered and used
  for continuous sync — including changes made from the matrix's own front panel.
- If no query works, the integration stops probing (to keep polls fast) and Home Assistant
  **keeps its last known state**, updating whenever you switch from Home Assistant.

If polling doesn't pick up front-panel changes, capture your unit's real reply and tune it:

1. Add to `configuration.yaml` and restart:
   ```yaml
   logger:
     logs:
       custom_components.mt_viki_matrix: debug
   ```
2. Watch the log; raw replies are logged as `Query ... raw reply: ...` and
   `Switch ... reply: ...`.
3. Add the working command to `QUERY_COMMANDS` in `const.py` (or open an issue with the
   captured reply) so passive polling can read state too.

## Development

The state parser is a pure function with no network or Home Assistant dependency:

```bash
pip install pytest
pytest tests/test_parse.py
```

## Notes

- The matrix geometry (8×8) is set by `INPUTS` / `OUTPUTS` in `const.py`; change them to
  target a 4×4 or 16×16 unit from the same family.
- This is an unofficial, community integration and is not affiliated with MT-VIKI.
