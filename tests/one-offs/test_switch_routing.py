#!/usr/bin/env python
"""
One-off tests for DazzleSwitch.switch() routing logic.

Tests all selection priority paths without ComfyUI dependencies.
py/node.py only imports logging, so we can import directly.

Usage:
    python tests/one-offs/test_switch_logic.py
    python tests/one-offs/test_switch_logic.py -v
"""

import sys
import os

# Add project root to path so we can import py.node directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from py.node import DazzleSwitch, AnyType, any_type, FlexibleOptionalInputType


def test_anytype_ne_returns_false():
    """AnyType.__ne__ should return False for any comparison."""
    t = AnyType("*")
    assert not (t != "IMAGE"), "AnyType != 'IMAGE' should be False"
    assert not (t != "MASK"), "AnyType != 'MASK' should be False"
    assert not (t != "MODEL"), "AnyType != 'MODEL' should be False"
    assert not (t != "STRING"), "AnyType != 'STRING' should be False"
    assert not (t != 42), "AnyType != 42 should be False"
    assert not (t != None), "AnyType != None should be False"
    assert not (t != t), "AnyType != itself should be False"
    print("  PASS: AnyType.__ne__ returns False for all comparisons")


def test_anytype_is_str():
    """AnyType should be a str subclass with value '*'."""
    t = AnyType("*")
    assert isinstance(t, str), "AnyType should be a str"
    assert t == "*", "AnyType('*') should equal '*'"
    print("  PASS: AnyType is str subclass with value '*'")


def test_input_types_structure():
    """INPUT_TYPES should have the expected structure."""
    it = DazzleSwitch.INPUT_TYPES()

    assert "required" in it
    assert "optional" in it
    assert "hidden" in it

    # Required: select combo
    assert "select" in it["required"]

    # Optional should be FlexibleOptionalInputType
    opt = it["optional"]
    assert isinstance(opt, FlexibleOptionalInputType), \
        f"optional should be FlexibleOptionalInputType, got {type(opt)}"

    # Declared: select_override + 3 initial inputs
    assert "select_override" in opt
    assert opt["select_override"][0] == "INT"
    for i in range(1, 4):
        key = f"input_{i:02d}"
        assert key in opt, f"Missing {key} in initial optional inputs"

    # Undeclared inputs should also be accepted (FlexibleOptionalInputType)
    assert "input_04" in opt, "FlexibleOptionalInputType should accept input_04"
    assert "input_99" in opt, "FlexibleOptionalInputType should accept input_99"

    # Hidden: unique_id
    assert "unique_id" in it["hidden"]

    print("  PASS: INPUT_TYPES has correct structure (3 initial + flexible)")


def test_class_attributes():
    """Class attributes should be set correctly."""
    assert DazzleSwitch.FUNCTION == "switch"
    assert DazzleSwitch.CATEGORY == "DazzleNodes"
    assert DazzleSwitch.OUTPUT_NODE == False
    assert len(DazzleSwitch.RETURN_TYPES) == 2
    assert DazzleSwitch.RETURN_TYPES[1] == "INT"
    assert DazzleSwitch.RETURN_NAMES == ("output", "selected_index")
    print("  PASS: Class attributes are correct")


def test_no_inputs_connected():
    """With no inputs connected, should return (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none connected)", select_override=0, unique_id="test")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: No inputs -> (None, 0)")


def test_no_inputs_with_override():
    """Override with no inputs should still return (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none connected)", select_override=3, unique_id="test")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: Override + no inputs -> (None, 0)")


def test_single_input_dropdown():
    """Single connected input selected via dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", select_override=0, unique_id="test",
                       input_01="model_A")
    assert result == ("model_A", 1), f"Expected ('model_A', 1), got {result}"
    print("  PASS: Single input via dropdown -> correct value + index")


def test_dropdown_selects_specific_input():
    """Dropdown should select the specified input, not just the first."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_03", select_override=0, unique_id="test",
                       input_01="model_A", input_02="model_B", input_03="model_C")
    assert result == ("model_C", 3), f"Expected ('model_C', 3), got {result}"
    print("  PASS: Dropdown selects input_03 correctly")


def test_override_takes_priority():
    """INT override should take priority over dropdown."""
    ds = DazzleSwitch()
    # Dropdown says input_01, but override says 2
    result = ds.switch(select="input_01", select_override=2, unique_id="test",
                       input_01="model_A", input_02="model_B")
    assert result == ("model_B", 2), f"Expected ('model_B', 2), got {result}"
    print("  PASS: Override=2 beats dropdown=input_01")


def test_override_zero_uses_dropdown():
    """Override=0 should defer to dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_02", select_override=0, unique_id="test",
                       input_01="model_A", input_02="model_B")
    assert result == ("model_B", 2), f"Expected ('model_B', 2), got {result}"
    print("  PASS: Override=0 defers to dropdown")


def test_override_disconnected_falls_back_to_dropdown():
    """Override pointing to disconnected input should fall back to dropdown."""
    ds = DazzleSwitch()
    # Override says input_04 but only 1-2 are connected, dropdown says input_02
    result = ds.switch(select="input_02", select_override=4, unique_id="test",
                       input_01="model_A", input_02="model_B")
    assert result == ("model_B", 2), f"Expected ('model_B', 2), got {result}"
    print("  PASS: Override=4 (disconnected) falls back to dropdown=input_02")


def test_dropdown_disconnected_falls_back_to_first():
    """Dropdown pointing to disconnected input should fall back to first connected."""
    ds = DazzleSwitch()
    # Dropdown says input_03 but only 1 and 5 are connected
    result = ds.switch(select="input_03", select_override=0, unique_id="test",
                       input_01="model_A", input_05="model_E")
    assert result == ("model_A", 1), f"Expected ('model_A', 1), got {result}"
    print("  PASS: Dropdown=input_03 (disconnected) falls back to first connected (input_01)")


def test_both_override_and_dropdown_disconnected():
    """Both override and dropdown targets disconnected -> first connected."""
    ds = DazzleSwitch()
    # Override=4 (disconnected), dropdown=input_03 (disconnected), only input_02 connected
    result = ds.switch(select="input_03", select_override=4, unique_id="test",
                       input_02="model_B")
    assert result == ("model_B", 2), f"Expected ('model_B', 2), got {result}"
    print("  PASS: Both override+dropdown disconnected -> first connected (input_02)")


def test_none_values_treated_as_disconnected():
    """Inputs passed as None should be treated as disconnected."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", select_override=0, unique_id="test",
                       input_01=None, input_02="model_B", input_03=None)
    # input_01 is None so dropdown target is disconnected, falls back to first connected
    assert result == ("model_B", 2), f"Expected ('model_B', 2), got {result}"
    print("  PASS: None inputs treated as disconnected")


def test_all_five_inputs():
    """All 5 inputs connected, select each one."""
    ds = DazzleSwitch()
    values = {"input_01": "A", "input_02": "B", "input_03": "C",
              "input_04": "D", "input_05": "E"}

    for i in range(1, 6):
        key = f"input_{i:02d}"
        expected_val = chr(64 + i)  # A, B, C, D, E

        # Test via dropdown
        result = ds.switch(select=key, select_override=0, unique_id="test", **values)
        assert result == (expected_val, i), f"Dropdown {key}: expected ({expected_val}, {i}), got {result}"

        # Test via override
        result = ds.switch(select="input_01", select_override=i, unique_id="test", **values)
        assert result == (expected_val, i), f"Override {i}: expected ({expected_val}, {i}), got {result}"

    print("  PASS: All 5 inputs selectable via dropdown and override")


def test_override_beyond_connected():
    """Override pointing to unconnected input should fall back to dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", select_override=10, unique_id="test",
                       input_01="model_A")
    assert result == ("model_A", 1), f"Expected ('model_A', 1), got {result}"
    print("  PASS: Override=10 (not connected) falls back to dropdown")


def test_various_data_types():
    """Switch should pass through any data type without modification."""
    ds = DazzleSwitch()

    test_cases = [
        ("string", "hello world"),
        ("int", 42),
        ("float", 3.14),
        ("list", [1, 2, 3]),
        ("dict", {"key": "value"}),
        ("tuple", (1, 2)),
        ("bool", True),
        ("nested", {"a": [1, {"b": 2}]}),
    ]

    for type_name, value in test_cases:
        result = ds.switch(select="input_01", select_override=0, unique_id="test",
                           input_01=value)
        assert result[0] is value, f"{type_name}: expected same object, got different"
        assert result[1] == 1

    print(f"  PASS: {len(test_cases)} data types pass through without modification")


def test_node_registration_mappings():
    """NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS should be correct."""
    from py.node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    assert "DazzleSwitch" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["DazzleSwitch"] is DazzleSwitch
    assert "DazzleSwitch" in NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["DazzleSwitch"] == "Dazzle Switch (DazzleNodes)"
    print("  PASS: Registration mappings are correct")


## ── Phase 2: FlexibleOptionalInputType tests ─────────────────────────────────


def test_flexible_type_contains_any_key():
    """FlexibleOptionalInputType.__contains__ should return True for any key."""
    fot = FlexibleOptionalInputType(any_type)
    assert "input_01" in fot
    assert "input_99" in fot
    assert "anything" in fot
    assert "nonexistent_key" in fot
    print("  PASS: FlexibleOptionalInputType accepts any key via __contains__")


def test_flexible_type_declared_keys():
    """FlexibleOptionalInputType should return declared values for known keys."""
    fot = FlexibleOptionalInputType(any_type, {
        "select_override": ("INT", {"default": 0}),
        "input_01": (any_type, {}),
    })
    assert fot["select_override"] == ("INT", {"default": 0})
    assert fot["input_01"] == (any_type, {})
    print("  PASS: FlexibleOptionalInputType returns declared values for known keys")


def test_flexible_type_undeclared_keys():
    """FlexibleOptionalInputType should return (any_type,) for unknown keys."""
    fot = FlexibleOptionalInputType(any_type, {
        "input_01": (any_type, {}),
    })
    result = fot["input_04"]
    assert result == (any_type,), f"Expected (any_type,), got {result}"
    result = fot["input_99"]
    assert result == (any_type,), f"Expected (any_type,), got {result}"
    print("  PASS: FlexibleOptionalInputType returns (any_type,) for undeclared keys")


## ── Phase 2: Dynamic input kwargs tests ──────────────────────────────────────


def test_dynamic_input_06():
    """switch() should accept input_06 via kwargs (not declared in INPUT_TYPES)."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_06", select_override=0, unique_id="test",
                       input_06="model_F")
    assert result == ("model_F", 6), f"Expected ('model_F', 6), got {result}"
    print("  PASS: Dynamic input_06 works via dropdown")


def test_dynamic_input_override():
    """Override should work with dynamic inputs beyond initial 3."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", select_override=7, unique_id="test",
                       input_01="A", input_07="G")
    assert result == ("G", 7), f"Expected ('G', 7), got {result}"
    print("  PASS: Override=7 selects dynamic input_07")


def test_many_dynamic_inputs():
    """switch() should handle many dynamic inputs (up to input_15)."""
    ds = DazzleSwitch()
    values = {f"input_{i:02d}": chr(64 + i) for i in range(1, 16)}

    # Test input_15 via dropdown
    result = ds.switch(select="input_15", select_override=0, unique_id="test", **values)
    assert result == ("O", 15), f"Expected ('O', 15), got {result}"

    # Test input_10 via override
    result = ds.switch(select="input_01", select_override=10, unique_id="test", **values)
    assert result == ("J", 10), f"Expected ('J', 10), got {result}"

    print("  PASS: 15 dynamic inputs work correctly")


def test_non_input_kwargs_ignored():
    """kwargs that don't match input_XX pattern should be ignored."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", select_override=0, unique_id="test",
                       input_01="A", random_key="should_ignore", input="also_ignore")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Non-input_XX kwargs are ignored")


def test_mixed_declared_and_dynamic():
    """Mix of declared (01-03) and dynamic (04-06) inputs should all work."""
    ds = DazzleSwitch()
    values = {f"input_{i:02d}": f"val_{i}" for i in range(1, 7)}

    for i in range(1, 7):
        key = f"input_{i:02d}"
        result = ds.switch(select=key, select_override=0, unique_id="test", **values)
        assert result == (f"val_{i}", i), f"{key}: expected ('val_{i}', {i}), got {result}"

    print("  PASS: Mixed declared + dynamic inputs (01-06) all work")


## ── Phase 2: VALIDATE_INPUTS tests ───────────────────────────────────────────


def test_validate_inputs_returns_true():
    """VALIDATE_INPUTS should return True for any select value."""
    assert DazzleSwitch.VALIDATE_INPUTS(select="input_01") is True
    assert DazzleSwitch.VALIDATE_INPUTS(select="input_99") is True
    assert DazzleSwitch.VALIDATE_INPUTS(select="(none connected)") is True
    assert DazzleSwitch.VALIDATE_INPUTS(select="anything") is True
    print("  PASS: VALIDATE_INPUTS returns True for any select value")


def test_validate_inputs_with_kwargs():
    """VALIDATE_INPUTS should accept arbitrary kwargs without error."""
    result = DazzleSwitch.VALIDATE_INPUTS(
        select="input_01", select_override=5,
        input_01="foo", input_99="bar"
    )
    assert result is True
    print("  PASS: VALIDATE_INPUTS handles arbitrary kwargs")


## ── Phase 2: Initial slot count tests ────────────────────────────────────────


def test_initial_slot_count_is_three():
    """INPUT_TYPES should declare exactly 3 input_XX slots (not 5)."""
    opt = DazzleSwitch.INPUT_TYPES()["optional"]
    declared_inputs = [k for k in opt.keys() if k.startswith("input_")]
    assert len(declared_inputs) == 3, \
        f"Expected 3 declared input slots, got {len(declared_inputs)}: {declared_inputs}"
    assert declared_inputs == ["input_01", "input_02", "input_03"]
    print("  PASS: Exactly 3 input_XX slots declared in INPUT_TYPES")


def test_select_override_max_is_50():
    """select_override max should be 50, supporting up to input_50."""
    opt = DazzleSwitch.INPUT_TYPES()["optional"]
    override_config = opt["select_override"]
    assert override_config[1]["max"] == 50, \
        f"Expected max=50, got {override_config[1]['max']}"
    print("  PASS: select_override max is 50")


## ── Phase 2: Regex edge case tests ──────────────────────────────────────────


def test_input_regex_rejects_bad_names():
    """switch() should ignore kwargs that almost match input_XX but don't."""
    ds = DazzleSwitch()

    # Single digit (input_1 instead of input_01)
    result = ds.switch(select="(none connected)", select_override=0, unique_id="test",
                       input_1="should_ignore")
    assert result == (None, 0), f"input_1 should be ignored, got {result}"

    # Three digits (input_001)
    result = ds.switch(select="(none connected)", select_override=0, unique_id="test",
                       input_001="should_ignore")
    assert result == (None, 0), f"input_001 should be ignored, got {result}"

    # No underscore (input01)
    result = ds.switch(select="(none connected)", select_override=0, unique_id="test",
                       input01="should_ignore")
    assert result == (None, 0), f"input01 should be ignored, got {result}"

    # Prefix match (input_01_extra)
    result = ds.switch(select="(none connected)", select_override=0, unique_id="test",
                       input_01_extra="should_ignore")
    assert result == (None, 0), f"input_01_extra should be ignored, got {result}"

    print("  PASS: Regex rejects malformed input names (input_1, input_001, input01, input_01_extra)")


def test_input_regex_accepts_valid_range():
    """switch() should accept input_00 through input_99."""
    ds = DazzleSwitch()

    # input_00 is technically valid regex but unusual
    result = ds.switch(select="input_00", select_override=0, unique_id="test",
                       input_00="zero")
    assert result == ("zero", 0), f"Expected ('zero', 0), got {result}"

    # input_99 at the high end
    result = ds.switch(select="input_99", select_override=0, unique_id="test",
                       input_99="ninety_nine")
    assert result == ("ninety_nine", 99), f"Expected ('ninety_nine', 99), got {result}"

    print("  PASS: Regex accepts input_00 through input_99")


## ── Phase 2: FlexibleOptionalInputType edge cases ───────────────────────────


def test_flexible_type_empty_init():
    """FlexibleOptionalInputType with no initial data should still work."""
    fot = FlexibleOptionalInputType(any_type)
    assert "anything" in fot
    assert fot["input_01"] == (any_type,)
    assert len(fot) == 0  # no declared keys
    print("  PASS: FlexibleOptionalInputType works with no initial data")


def test_flexible_type_iteration():
    """Iterating FlexibleOptionalInputType should only yield declared keys."""
    fot = FlexibleOptionalInputType(any_type, {
        "select_override": ("INT", {}),
        "input_01": (any_type, {}),
        "input_02": (any_type, {}),
    })
    keys = list(fot.keys())
    assert len(keys) == 3, f"Expected 3 declared keys, got {len(keys)}: {keys}"
    assert "select_override" in keys
    assert "input_01" in keys
    assert "input_02" in keys
    # Undeclared keys don't appear in iteration
    assert "input_99" not in keys
    print("  PASS: FlexibleOptionalInputType iteration yields only declared keys")


## ── Phase 2: Connected input ordering tests ─────────────────────────────────


def test_fallback_uses_first_connected_by_insertion_order():
    """Fallback should select the first connected input by kwargs order."""
    ds = DazzleSwitch()
    # Only input_03 and input_05 connected, dropdown points to disconnected input_01
    result = ds.switch(select="input_01", select_override=0, unique_id="test",
                       input_03="C", input_05="E")
    # First connected in kwargs iteration order
    assert result[0] == "C", f"Expected 'C' as fallback, got {result[0]}"
    assert result[1] == 3, f"Expected index 3, got {result[1]}"
    print("  PASS: Fallback picks first connected input by insertion order")


def test_switch_with_sparse_high_inputs():
    """switch() handles sparse inputs at high numbers (input_20, input_45)."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_45", select_override=0, unique_id="test",
                       input_20="twenty", input_45="forty_five")
    assert result == ("forty_five", 45), f"Expected ('forty_five', 45), got {result}"

    # Override to 20
    result = ds.switch(select="input_45", select_override=20, unique_id="test",
                       input_20="twenty", input_45="forty_five")
    assert result == ("twenty", 20), f"Expected ('twenty', 20), got {result}"
    print("  PASS: Sparse high-number inputs work (input_20, input_45)")


# ── Phase 4: Fallback mode tests ─────────────────────────────────────────────

def test_mode_widget_in_input_types():
    """INPUT_TYPES should include mode combo with three options."""
    it = DazzleSwitch.INPUT_TYPES()
    assert "mode" in it["required"], "mode widget missing from required inputs"
    mode_opts = it["required"]["mode"][0]
    assert mode_opts == ["priority", "strict", "sequential"], \
        f"Expected ['priority', 'strict', 'sequential'], got {mode_opts}"
    assert it["required"]["mode"][1]["default"] == "priority", \
        "Default mode should be 'priority'"
    print("  PASS: mode widget in INPUT_TYPES with correct options and default")


def test_priority_requested_available():
    """Priority mode: requested input available → returns it (happy path)."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_02", mode="priority", select_override=0,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Priority mode returns requested when available")


def test_priority_requested_unavailable():
    """Priority mode: requested unavailable → first non-None from top."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_04", mode="priority", select_override=0,
                       unique_id="test", input_02="B", input_05="E")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Priority mode falls back to first from top (input_02)")


def test_priority_with_override_miss():
    """Priority mode: override misses, dropdown misses → first from top."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_04", mode="priority", select_override=6,
                       unique_id="test", input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Priority mode: override+dropdown miss -> first from top")


def test_priority_override_miss_dropdown_hit():
    """Priority mode: override misses but dropdown hits → returns dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_02", mode="priority", select_override=5,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Priority mode: override misses, dropdown hits -> dropdown wins")


def test_priority_all_none():
    """Priority mode: all inputs None → (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="priority", select_override=0,
                       unique_id="test", input_01=None, input_02=None)
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: Priority mode: all None -> (None, 0)")


def test_strict_requested_available():
    """Strict mode: requested available → returns it."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_02", mode="strict", select_override=0,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Strict mode returns requested when available")


def test_strict_requested_unavailable():
    """Strict mode: requested unavailable → (None, 0), no fallback."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_04", mode="strict", select_override=0,
                       unique_id="test", input_01="A", input_02="B")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: Strict mode: requested unavailable -> (None, 0)")


def test_strict_override_miss_dropdown_hit():
    """Strict mode: override misses but dropdown hits → returns dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="strict", select_override=5,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Strict mode: override misses, dropdown hits -> dropdown wins")


def test_strict_both_miss():
    """Strict mode: override and dropdown both miss → (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_04", mode="strict", select_override=6,
                       unique_id="test", input_01="A", input_02="B")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: Strict mode: both miss -> (None, 0)")


def test_sequential_requested_available():
    """Sequential mode: requested available → returns it."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_02", mode="sequential", select_override=0,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Sequential mode returns requested when available")


def test_sequential_next_slot():
    """Sequential mode: requested unavailable → next connected slot."""
    ds = DazzleSwitch()
    # input_02 selected but unavailable (None), input_03 is next
    result = ds.switch(select="input_02", mode="sequential", select_override=0,
                       unique_id="test", input_01="A", input_02=None, input_03="C")
    assert result == ("C", 3), f"Expected ('C', 3), got {result}"
    print("  PASS: Sequential mode: input_02 unavailable -> next is input_03")


def test_sequential_skips_none():
    """Sequential mode: skips None slots in scan."""
    ds = DazzleSwitch()
    # input_02 selected but unavailable, input_03 also None, input_04 is next
    result = ds.switch(select="input_02", mode="sequential", select_override=0,
                       unique_id="test", input_01="A", input_02=None,
                       input_03=None, input_04="D")
    assert result == ("D", 4), f"Expected ('D', 4), got {result}"
    print("  PASS: Sequential mode skips None slots (input_03) to reach input_04")


def test_sequential_wraps_around():
    """Sequential mode: wraps from last slot back to first."""
    ds = DazzleSwitch()
    # input_04 selected but unavailable, nothing after → wraps to input_01
    result = ds.switch(select="input_04", mode="sequential", select_override=0,
                       unique_id="test", input_01="A", input_02=None,
                       input_03=None, input_04=None)
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Sequential mode wraps around to input_01")


def test_sequential_override_miss_dropdown_hit():
    """Sequential mode: override misses but dropdown hits → returns dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_02", mode="sequential", select_override=5,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Sequential mode: override misses, dropdown hits -> dropdown wins")



def test_sequential_both_miss_scans_forward():
    """Sequential mode: both override and dropdown miss → scans forward from override position."""
    ds = DazzleSwitch()
    # override=4 (miss — not connected), dropdown=input_06 (miss — not connected)
    # full slot range: [input_01, input_02, input_03, input_04] (max of connected=3, override=4)
    # start_pos=3 (input_04), scan forward: wraps to input_01 ("A", connected!)
    result = ds.switch(select="input_06", mode="sequential", select_override=4,
                       unique_id="test", input_01="A", input_02=None, input_03="C")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Sequential mode: both miss, scans forward from override position")


def test_sequential_all_none():
    """Sequential mode: all inputs None → (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="sequential", select_override=0,
                       unique_id="test", input_01=None, input_02=None)
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: Sequential mode: all None -> (None, 0)")


def test_mode_single_input_all_modes():
    """All modes behave identically with a single connected input."""
    ds = DazzleSwitch()
    for mode in ["priority", "strict", "sequential"]:
        result = ds.switch(select="input_01", mode=mode, select_override=0,
                           unique_id="test", input_01="only_one")
        assert result == ("only_one", 1), \
            f"Mode {mode}: Expected ('only_one', 1), got {result}"
    print("  PASS: All modes return the single connected input")


def test_selected_index_reflects_actual_not_requested():
    """selected_index should reflect what was actually used, not what was requested."""
    ds = DazzleSwitch()
    # Request input_03 (unavailable), priority falls back to input_01
    result = ds.switch(select="input_03", mode="priority", select_override=0,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("A", 1), f"Expected index 1 (actual), got {result}"
    print("  PASS: selected_index reflects actual result (1), not request (3)")


# ── Phase 4: (none) dropdown bypass tests ─────────────────────────────────────

def test_none_constants_on_class():
    """DazzleSwitch should have NONE_SELECTION and NO_CONNECTIONS constants."""
    assert DazzleSwitch.NONE_SELECTION == "(none)"
    assert DazzleSwitch.NO_CONNECTIONS == "(none connected)"
    print("  PASS: NONE_SELECTION and NO_CONNECTIONS constants defined")


def test_none_priority_is_true_rgthree():
    """(none) + priority = true rgthree behavior: first from top, no dropdown."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="priority", select_override=0,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: (none) + priority -> first from top (true rgthree)")


def test_none_priority_skips_none_values():
    """(none) + priority: skips None inputs, picks first non-None."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="priority", select_override=0,
                       unique_id="test", input_01=None, input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: (none) + priority -> skips None, picks input_02")


def test_none_strict_no_override():
    """(none) + strict + no override = (None, 0) — nothing to try."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="strict", select_override=0,
                       unique_id="test", input_01="A", input_02="B")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: (none) + strict + no override -> (None, 0)")


def test_none_strict_with_override_hit():
    """(none) + strict + override hits = returns override target."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="strict", select_override=2,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: (none) + strict + override=2 -> ('B', 2)")


def test_none_strict_with_override_miss():
    """(none) + strict + override misses = (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="strict", select_override=5,
                       unique_id="test", input_01="A", input_02="B")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: (none) + strict + override=5 (miss) -> (None, 0)")


def test_none_sequential_scans_from_top():
    """(none) + sequential + no override = scans from top (like priority but sequential)."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="sequential", select_override=0,
                       unique_id="test", input_01=None, input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: (none) + sequential -> scans from top, finds input_02")


def test_none_sequential_with_override_miss():
    """(none) + sequential + override misses = scans from override position."""
    ds = DazzleSwitch()
    # override=2, input_02 is None, scans forward: input_03 is "C"
    result = ds.switch(select="(none)", mode="sequential", select_override=2,
                       unique_id="test", input_01="A", input_02=None, input_03="C")
    assert result == ("C", 3), f"Expected ('C', 3), got {result}"
    print("  PASS: (none) + sequential + override=2 miss -> scans to input_03")


def test_none_with_override_hit():
    """(none) + any mode: override still takes priority when it hits."""
    ds = DazzleSwitch()
    for mode in ["priority", "strict", "sequential"]:
        result = ds.switch(select="(none)", mode=mode, select_override=2,
                           unique_id="test", input_01="A", input_02="B", input_03="C")
        assert result == ("B", 2), f"Mode {mode}: Expected ('B', 2), got {result}"
    print("  PASS: (none) + override hit -> override wins in all modes")


def test_none_no_inputs_connected():
    """(none) with no connected inputs -> (None, 0)."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="priority", select_override=0,
                       unique_id="test")
    assert result == (None, 0), f"Expected (None, 0), got {result}"
    print("  PASS: (none) + no inputs -> (None, 0)")


def test_none_connected_also_bypasses():
    """(none connected) should also bypass dropdown (backward compat)."""
    ds = DazzleSwitch()
    # Even though inputs exist, (none connected) means "no dropdown preference"
    result = ds.switch(select="(none connected)", mode="priority", select_override=0,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: (none connected) also bypasses dropdown -> priority fallback")


def test_dropdown_still_works_with_none_option_available():
    """When user selects an actual input (not (none)), dropdown still participates."""
    ds = DazzleSwitch()
    # User explicitly selects input_03 — dropdown should still work
    result = ds.switch(select="input_03", mode="priority", select_override=0,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("C", 3), f"Expected ('C', 3), got {result}"
    print("  PASS: Dropdown still works when user selects an actual input")


# ── Phase 4: Negative indexing tests ──────────────────────────────────────────

def test_negative_one_selects_last_connected():
    """-1 should select the last connected input."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="priority", select_override=-1,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("C", 3), f"Expected ('C', 3), got {result}"
    print("  PASS: override=-1 selects last connected (input_03)")


def test_negative_two_selects_second_to_last():
    """-2 should select the second-to-last connected input."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="priority", select_override=-2,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: override=-2 selects second-to-last (input_02)")


def test_negative_with_sparse_inputs():
    """-1 on sparse inputs should select the highest-numbered connected."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="priority", select_override=-1,
                       unique_id="test", input_02="B", input_05="E", input_08="H")
    assert result == ("H", 8), f"Expected ('H', 8), got {result}"
    print("  PASS: override=-1 with sparse inputs -> input_08 (highest)")


def test_negative_skips_none_values():
    """-1 should only count connected (non-None) inputs."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="priority", select_override=-1,
                       unique_id="test", input_01="A", input_02=None, input_03="C",
                       input_04=None)
    assert result == ("C", 3), f"Expected ('C', 3), got {result}"
    print("  PASS: override=-1 skips None, selects input_03")


def test_negative_out_of_range_falls_through():
    """-5 with only 2 connected should fall through to dropdown/mode."""
    ds = DazzleSwitch()
    result = ds.switch(select="input_01", mode="priority", select_override=-5,
                       unique_id="test", input_01="A", input_03="C")
    # -5 out of range (only 2 connected), falls to dropdown (input_01)
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: override=-5 out of range -> falls through to dropdown")


def test_negative_out_of_range_with_none_dropdown():
    """-5 out of range + (none) dropdown -> mode fallback."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="priority", select_override=-5,
                       unique_id="test", input_02="B", input_04="D")
    # -5 out of range, dropdown skipped, priority -> first from top
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: override=-5 out of range + (none) -> priority fallback")


def test_negative_one_single_input():
    """-1 with single connected input returns that input."""
    ds = DazzleSwitch()
    result = ds.switch(select="(none)", mode="strict", select_override=-1,
                       unique_id="test", input_03="C")
    assert result == ("C", 3), f"Expected ('C', 3), got {result}"
    print("  PASS: override=-1 with single input -> returns it")


def test_negative_override_min_is_negative_50():
    """select_override min should be -50."""
    opt = DazzleSwitch.INPUT_TYPES()["optional"]
    override_config = opt["select_override"]
    assert override_config[1]["min"] == -50, \
        f"Expected min=-50, got {override_config[1]['min']}"
    print("  PASS: select_override min is -50")


# ── Phase 4: Sequential gap-awareness tests ─────────────────────────────────
# These tests simulate ComfyUI's actual behavior: disconnected inputs are
# OMITTED from kwargs entirely (not passed as None).

def test_sequential_gap_override_targets_disconnected():
    """Override targets disconnected slot (omitted from kwargs) → next connected."""
    ds = DazzleSwitch()
    # input_03 is physically disconnected — NOT in kwargs at all
    # Sequential should scan forward from position 3 → find input_04
    result = ds.switch(select="(none)", mode="sequential", select_override=3,
                       unique_id="test", input_01="A", input_02="B",
                       input_04="D", input_05="E")
    assert result == ("D", 4), f"Expected ('D', 4), got {result}"
    print("  PASS: Sequential gap: override=3 (disconnected) -> input_04")


def test_sequential_gap_multiple_consecutive():
    """Multiple consecutive disconnected slots → skips all gaps."""
    ds = DazzleSwitch()
    # input_02, 03, 04 all disconnected — scan from 2 should reach 05
    result = ds.switch(select="(none)", mode="sequential", select_override=2,
                       unique_id="test", input_01="A", input_05="E")
    assert result == ("E", 5), f"Expected ('E', 5), got {result}"
    print("  PASS: Sequential gap: override=2, slots 2-4 disconnected -> input_05")


def test_sequential_gap_wraps_around():
    """Override targets gap near end → wraps to beginning."""
    ds = DazzleSwitch()
    # input_04 and 05 disconnected, only 01 and 02 connected
    result = ds.switch(select="(none)", mode="sequential", select_override=4,
                       unique_id="test", input_01="A", input_02="B",
                       input_05="E")
    assert result == ("E", 5), f"Expected ('E', 5), got {result}"
    print("  PASS: Sequential gap: override=4 (disconnected) -> wraps to input_05")


def test_sequential_gap_wraps_past_all_trailing():
    """Override targets gap, nothing after → wraps to first connected."""
    ds = DazzleSwitch()
    # override=4, only 01 and 02 connected, 03 and 04 absent
    result = ds.switch(select="(none)", mode="sequential", select_override=4,
                       unique_id="test", input_01="A", input_02="B")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Sequential gap: override=4 past all -> wraps to input_01")


def test_sequential_gap_at_position_1():
    """Gap at position 1, override=1 → next connected."""
    ds = DazzleSwitch()
    # input_01 disconnected, input_02 connected
    result = ds.switch(select="(none)", mode="sequential", select_override=1,
                       unique_id="test", input_02="B", input_03="C")
    assert result == ("B", 2), f"Expected ('B', 2), got {result}"
    print("  PASS: Sequential gap: override=1 (disconnected) -> input_02")


def test_sequential_gap_override_beyond_max():
    """Override points beyond all physical slots → wraps to first connected."""
    ds = DazzleSwitch()
    # Only 3 slots exist, override=7
    result = ds.switch(select="(none)", mode="sequential", select_override=7,
                       unique_id="test", input_01="A", input_02="B", input_03="C")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Sequential gap: override=7 beyond max -> wraps to input_01")


def test_sequential_gap_none_vs_omitted_equivalence():
    """Passing input=None vs omitting it entirely should produce same result."""
    ds = DazzleSwitch()
    # Scenario: override=3, input_03 disconnected, should reach input_04

    # ComfyUI style: input_03 omitted entirely
    result_omitted = ds.switch(select="(none)", mode="sequential", select_override=3,
                               unique_id="test", input_01="A", input_02="B",
                               input_04="D")

    # Test style: input_03 passed as None
    result_none = ds.switch(select="(none)", mode="sequential", select_override=3,
                            unique_id="test", input_01="A", input_02="B",
                            input_03=None, input_04="D")

    assert result_omitted == result_none == ("D", 4), \
        f"Omitted: {result_omitted}, None: {result_none}, Expected: ('D', 4)"
    print("  PASS: Sequential gap: omitted vs None produce identical results")


def test_build_full_slot_range_basic():
    """_build_full_slot_range generates correct range from connected keys."""
    ds = DazzleSwitch()
    connected = {"input_01": ("A", 1), "input_03": ("C", 3), "input_05": ("E", 5)}
    result = ds._build_full_slot_range(connected, None)
    assert result == ["input_01", "input_02", "input_03", "input_04", "input_05"], \
        f"Expected 5-slot range, got {result}"
    print("  PASS: _build_full_slot_range: basic range from sparse connected")


def test_build_full_slot_range_extends_for_override():
    """_build_full_slot_range extends range when override is beyond max connected."""
    ds = DazzleSwitch()
    connected = {"input_01": ("A", 1), "input_02": ("B", 2)}
    result = ds._build_full_slot_range(connected, "input_05")
    assert result == ["input_01", "input_02", "input_03", "input_04", "input_05"], \
        f"Expected 5-slot range, got {result}"
    print("  PASS: _build_full_slot_range: extends range for override beyond max")


def test_sequential_gap_last_slot_disconnected_wraps():
    """Override targets last slot which is disconnected → wraps to input_01."""
    ds = DazzleSwitch()
    # input_05 is the last slot, disconnected. Should wrap to input_01.
    result = ds.switch(select="(none)", mode="sequential", select_override=5,
                       unique_id="test", input_01="A", input_02="B", input_04="D")
    assert result == ("A", 1), f"Expected ('A', 1), got {result}"
    print("  PASS: Sequential gap: override=5 (last, disconnected) -> wraps to input_01")


def test_sequential_exact_bug_scenario():
    """Exact scenario from the user's bug report.

    {select=(none), mode=sequential, override=3}
    Slots: 1:SEED(5225), 2:int-reroute(2525), 3:another-int(DISCONNECTED), 4:float(3.14), 5:image(IMG)
    Expected: input_04 (3.14) — next connected after the gap at 3
    """
    ds = DazzleSwitch()
    result = ds.switch(
        select="(none)", mode="sequential", select_override=3,
        unique_id="test",
        input_01=5225,       # SEED
        input_02=2525,       # int-reroute
        # input_03 omitted — disconnected
        input_04=3.14,       # float
        input_05="IMG",      # image
    )
    assert result == (3.14, 4), f"Expected (3.14, 4), got {result}"
    print("  PASS: Exact bug scenario: override=3 (disconnected) -> input_04 (3.14)")


def main():
    tests = [
        # Phase 1 tests
        ("AnyType.__ne__ returns False", test_anytype_ne_returns_false),
        ("AnyType is str subclass", test_anytype_is_str),
        ("INPUT_TYPES structure", test_input_types_structure),
        ("Class attributes", test_class_attributes),
        ("No inputs connected", test_no_inputs_connected),
        ("No inputs with override", test_no_inputs_with_override),
        ("Single input via dropdown", test_single_input_dropdown),
        ("Dropdown selects specific input", test_dropdown_selects_specific_input),
        ("Override takes priority", test_override_takes_priority),
        ("Override=0 uses dropdown", test_override_zero_uses_dropdown),
        ("Override disconnected -> dropdown", test_override_disconnected_falls_back_to_dropdown),
        ("Dropdown disconnected -> first", test_dropdown_disconnected_falls_back_to_first),
        ("Both disconnected -> first", test_both_override_and_dropdown_disconnected),
        ("None values = disconnected", test_none_values_treated_as_disconnected),
        ("All 5 inputs selectable", test_all_five_inputs),
        ("Override beyond connected", test_override_beyond_connected),
        ("Various data types", test_various_data_types),
        ("Registration mappings", test_node_registration_mappings),
        # Phase 2 tests
        ("FlexibleOptionalInputType __contains__", test_flexible_type_contains_any_key),
        ("FlexibleOptionalInputType declared keys", test_flexible_type_declared_keys),
        ("FlexibleOptionalInputType undeclared keys", test_flexible_type_undeclared_keys),
        ("Dynamic input_06 via dropdown", test_dynamic_input_06),
        ("Dynamic input_07 via override", test_dynamic_input_override),
        ("15 dynamic inputs", test_many_dynamic_inputs),
        ("Non-input kwargs ignored", test_non_input_kwargs_ignored),
        ("Mixed declared + dynamic inputs", test_mixed_declared_and_dynamic),
        # Phase 2: VALIDATE_INPUTS
        ("VALIDATE_INPUTS returns True", test_validate_inputs_returns_true),
        ("VALIDATE_INPUTS with kwargs", test_validate_inputs_with_kwargs),
        # Phase 2: Initial slot count
        ("Initial slot count is 3", test_initial_slot_count_is_three),
        ("select_override max is 50", test_select_override_max_is_50),
        # Phase 2: Regex edge cases
        ("Regex rejects bad input names", test_input_regex_rejects_bad_names),
        ("Regex accepts input_00 to input_99", test_input_regex_accepts_valid_range),
        # Phase 2: FlexibleOptionalInputType edge cases
        ("FlexibleOptionalInputType empty init", test_flexible_type_empty_init),
        ("FlexibleOptionalInputType iteration", test_flexible_type_iteration),
        # Phase 2: Ordering and sparse inputs
        ("Fallback uses first connected", test_fallback_uses_first_connected_by_insertion_order),
        ("Sparse high-number inputs", test_switch_with_sparse_high_inputs),
        # Phase 4: Fallback modes
        ("Mode widget in INPUT_TYPES", test_mode_widget_in_input_types),
        ("Priority: requested available", test_priority_requested_available),
        ("Priority: requested unavailable", test_priority_requested_unavailable),
        ("Priority: override+dropdown miss", test_priority_with_override_miss),
        ("Priority: override miss, dropdown hit", test_priority_override_miss_dropdown_hit),
        ("Priority: all None", test_priority_all_none),
        ("Strict: requested available", test_strict_requested_available),
        ("Strict: requested unavailable", test_strict_requested_unavailable),
        ("Strict: override miss, dropdown hit", test_strict_override_miss_dropdown_hit),
        ("Strict: both miss", test_strict_both_miss),
        ("Sequential: requested available", test_sequential_requested_available),
        ("Sequential: next slot", test_sequential_next_slot),
        ("Sequential: skips None", test_sequential_skips_none),
        ("Sequential: wraps around", test_sequential_wraps_around),
        ("Sequential: override miss, dropdown hit", test_sequential_override_miss_dropdown_hit),
        ("Sequential: both miss, scans forward", test_sequential_both_miss_scans_forward),
        ("Sequential: all None", test_sequential_all_none),
        ("All modes: single input", test_mode_single_input_all_modes),
        ("selected_index reflects actual", test_selected_index_reflects_actual_not_requested),
        # Phase 4: (none) dropdown bypass
        ("(none) constants on class", test_none_constants_on_class),
        ("(none) + priority = true rgthree", test_none_priority_is_true_rgthree),
        ("(none) + priority skips None", test_none_priority_skips_none_values),
        ("(none) + strict + no override", test_none_strict_no_override),
        ("(none) + strict + override hit", test_none_strict_with_override_hit),
        ("(none) + strict + override miss", test_none_strict_with_override_miss),
        ("(none) + sequential from top", test_none_sequential_scans_from_top),
        ("(none) + sequential + override miss", test_none_sequential_with_override_miss),
        ("(none) + override hit all modes", test_none_with_override_hit),
        ("(none) + no inputs", test_none_no_inputs_connected),
        ("(none connected) also bypasses", test_none_connected_also_bypasses),
        ("Dropdown still works with (none) available", test_dropdown_still_works_with_none_option_available),
        # Phase 4: Negative indexing
        ("-1 selects last connected", test_negative_one_selects_last_connected),
        ("-2 selects second-to-last", test_negative_two_selects_second_to_last),
        ("-1 with sparse inputs", test_negative_with_sparse_inputs),
        ("-1 skips None values", test_negative_skips_none_values),
        ("-5 out of range falls through", test_negative_out_of_range_falls_through),
        ("-5 out of range + (none)", test_negative_out_of_range_with_none_dropdown),
        ("-1 single input", test_negative_one_single_input),
        ("select_override min is -50", test_negative_override_min_is_negative_50),
        # Phase 4: Sequential gap-awareness
        ("Sequential gap: override targets disconnected", test_sequential_gap_override_targets_disconnected),
        ("Sequential gap: multiple consecutive", test_sequential_gap_multiple_consecutive),
        ("Sequential gap: wraps around", test_sequential_gap_wraps_around),
        ("Sequential gap: wraps past all trailing", test_sequential_gap_wraps_past_all_trailing),
        ("Sequential gap: position 1", test_sequential_gap_at_position_1),
        ("Sequential gap: override beyond max", test_sequential_gap_override_beyond_max),
        ("Sequential gap: last slot disconnected wraps", test_sequential_gap_last_slot_disconnected_wraps),
        ("Sequential gap: None vs omitted equivalence", test_sequential_gap_none_vs_omitted_equivalence),
        ("_build_full_slot_range: basic", test_build_full_slot_range_basic),
        ("_build_full_slot_range: extends for override", test_build_full_slot_range_extends_for_override),
        ("Sequential gap: exact bug scenario", test_sequential_exact_bug_scenario),
    ]

    print(f"\nDazzleSwitch - Switch Logic Tests ({len(tests)} tests)")
    print("=" * 55)

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {name} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {name} - {type(e).__name__}: {e}")
            failed += 1

    print("=" * 55)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")

    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")


if __name__ == "__main__":
    main()
