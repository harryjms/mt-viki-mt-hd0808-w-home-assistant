"""Tests for the best-effort state parser.

These exercise ``parse_state_response`` without any network or Home Assistant
dependency, so they can run anywhere with plain pytest.
"""

import importlib
import importlib.util
import sys
import types
from pathlib import Path

# Load matrix.py directly so the test suite does not require Home Assistant to be
# installed just to reach the pure parser function. The integration's __init__.py
# imports Home Assistant, so we register a lightweight ``mt_viki_matrix`` package
# pointing at the component directory and import only ``matrix`` (which depends
# solely on the sibling ``const`` module).
_PKG_DIR = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "mt_viki_matrix"
)

_pkg = types.ModuleType("mt_viki_matrix")
_pkg.__path__ = [str(_PKG_DIR)]
sys.modules.setdefault("mt_viki_matrix", _pkg)

_matrix = importlib.import_module("mt_viki_matrix.matrix")
parse_state_response = _matrix.parse_state_response


def test_sws_status_line():
    # Confirmed MT-VIKI HD0808 format: reply to a "SW" command / status line.
    text = "SWS 1 2 3 4 5 1 7 8\r\n"
    result = parse_state_response(text, outputs=8, inputs=8)
    assert result == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 1, 7: 7, 8: 8}


def test_sws_wrong_count_falls_through():
    # An SWS line with too few numbers must not be accepted as complete state.
    assert parse_state_response("SWS 1 2 3\r\n", outputs=8, inputs=8) is None


def test_labelled_out_in_pairs():
    text = "OUT01 IN03\nOUT02 IN01\nOUT03 IN08\nOUT04 IN04\nOUT05 IN05\nOUT06 IN06\nOUT07 IN07\nOUT08 IN02\n"
    result = parse_state_response(text, outputs=8, inputs=8)
    assert result == {1: 3, 2: 1, 3: 8, 4: 4, 5: 5, 6: 6, 7: 7, 8: 2}


def test_word_form_pairs():
    text = "\n".join(f"Output {o}: Input {o}" for o in range(1, 9))
    result = parse_state_response(text, outputs=8, inputs=8)
    assert result == {o: o for o in range(1, 9)}


def test_arrow_pairs():
    text = "\n".join(f"Out {o} -> {9 - o}" for o in range(1, 9))
    result = parse_state_response(text, outputs=8, inputs=8)
    assert result == {o: 9 - o for o in range(1, 9)}


def test_compact_digit_table():
    # position N holds the input routed to output N
    text = "31845672\r\n"
    result = parse_state_response(text, outputs=8, inputs=8)
    assert result == {1: 3, 2: 1, 3: 8, 4: 4, 5: 5, 6: 6, 7: 7, 8: 2}


def test_unparseable_returns_none():
    assert parse_state_response("OK", outputs=8, inputs=8) is None
    assert parse_state_response("", outputs=8, inputs=8) is None
    assert parse_state_response("garbage 999 output", outputs=8, inputs=8) is None


def test_out_of_range_values_ignored():
    # Output 9 / input 9 are outside an 8x8 matrix and must be dropped.
    text = "OUT09 IN09\nOUT01 IN02\n"
    result = parse_state_response(text, outputs=8, inputs=8)
    assert result == {1: 2}
