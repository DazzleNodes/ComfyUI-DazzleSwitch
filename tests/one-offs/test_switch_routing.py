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
    assert NODE_DISPLAY_NAME_MAPPINGS["DazzleSwitch"] == "Dazzle Switch"
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
