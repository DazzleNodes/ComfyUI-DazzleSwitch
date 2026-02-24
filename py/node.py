"""
DazzleSwitch - Smart switch node with dropdown-based input selection.

Routes any ComfyUI data type through a user-selected dropdown,
with programmatic INT override for cascading workflows.
"""

import logging
import re

_logger = logging.getLogger("DazzleSwitch")


class AnyType(str):
    """Match any ComfyUI type via != comparison override.

    ComfyUI validates connections using `!=`. By always returning False,
    this type accepts connections from any other type.
    Credit: pythongosssss (community pattern).
    """

    def __ne__(self, other):
        return False


any_type = AnyType("*")


class FlexibleOptionalInputType(dict):
    """Dict subclass that accepts any key as a valid optional input.

    Tricks ComfyUI's validation into accepting dynamically-added inputs
    (e.g., input_04, input_05, ...) that aren't declared in INPUT_TYPES().
    When ComfyUI checks `if key in optional_inputs`, __contains__ returns True.
    When it fetches the type with `optional_inputs[key]`, __getitem__ returns
    the flexible type tuple.

    Pattern credit: rgthree (used in Any Switch and other dynamic nodes).
    """

    def __init__(self, type, initial=None):
        super().__init__()
        self.type = type
        if initial:
            self.update(initial)

    def __getitem__(self, key):
        if key in self.keys():
            return super().__getitem__(key)
        return (self.type,)

    def __contains__(self, key):
        return True


class DazzleSwitch:
    """Smart switch node — route any input via dropdown selection or INT override.

    Features:
    - Dynamic input slots that grow/shrink based on connections (minimum 3)
    - Dropdown widget dynamically populated by JS with connected input names
    - INT select_override for programmatic cascading (0 = use dropdown)
    - Outputs: selected value + 1-based index of which input was selected
    - Mixed type support: different types on different inputs (MODEL + IMAGE, etc.)
    """

    # Fallback modes — determines behavior when the selected input is unavailable
    MODES = ["priority", "strict", "sequential"]

    # Special dropdown values that bypass input selection
    NONE_SELECTION = "(none)"
    NO_CONNECTIONS = "(none connected)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "select": ([cls.NO_CONNECTIONS], {
                    "default": cls.NO_CONNECTIONS,
                    "tooltip": "Choose which connected input to route to output. "
                               "Select (none) to skip dropdown and let mode decide. "
                               "Options update automatically based on connections.",
                }),
                "mode": (cls.MODES, {
                    "default": "priority",
                    "tooltip": "Fallback when selected input is unavailable. "
                               "priority: first non-empty from top (rgthree-style). "
                               "strict: selected only, no fallback. "
                               "sequential: next slot down, wrapping around.",
                }),
            },
            "optional": FlexibleOptionalInputType(any_type, {
                "select_override": ("INT", {
                    "default": 0,
                    "min": -50,
                    "max": 50,
                    "tooltip": "Programmatic override: 0 = use dropdown, "
                               "1+ = select that input number directly, "
                               "-1 = last connected, -2 = second-to-last, etc. "
                               "Enables cascading selection from upstream.",
                }),
                "input_01": (any_type, {}),
                "input_02": (any_type, {}),
                "input_03": (any_type, {}),
            }),
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = (any_type, "INT")
    RETURN_NAMES = ("output", "selected_index")
    FUNCTION = "switch"
    CATEGORY = "DazzleNodes"
    OUTPUT_NODE = False

    @classmethod
    def VALIDATE_INPUTS(cls, select, **kwargs):
        """Bypass server-side combo validation for the select widget.

        The select dropdown is dynamically populated by JS with connected
        input names. The server only sees the static ["(none connected)"]
        list from INPUT_TYPES(), so any real selection would fail validation.
        """
        return True

    # Compiled once — matches input_01 through input_99
    _INPUT_RE = re.compile(r"^input_(\d{2})$")

    def _build_full_slot_range(self, connected, requested):
        """Build sorted list of all slot positions from 1 to max(connected, requested).

        Includes gap positions where slots exist but are disconnected.
        Used by sequential mode to scan forward through the full slot range,
        since ComfyUI omits disconnected inputs from kwargs entirely.
        """
        max_slot = 0
        for key in connected:
            m = self._INPUT_RE.match(key)
            if m:
                max_slot = max(max_slot, int(m.group(1)))
        if requested is not None:
            m = self._INPUT_RE.match(requested)
            if m:
                max_slot = max(max_slot, int(m.group(1)))
        return [f"input_{i:02d}" for i in range(1, max_slot + 1)]

    def switch(self, select="(none connected)", mode="priority",
               select_override=0, unique_id=None, **kwargs):
        """Route the selected input to output.

        Resolution chain:
        1. select_override < 0 → negative index (-1=last, -2=second-to-last)
        2. select_override > 0 → try that input by position
        3. If select is an input name (not "(none)") → try dropdown selection
        4. All missed or skipped → apply mode fallback

        When select is "(none)", step 3 is skipped entirely — the user is
        opting out of dropdown participation ("let the mode decide").
        """
        # Build dict of connected (non-None) inputs with their indices
        connected = {}
        for key, value in kwargs.items():
            m = self._INPUT_RE.match(key)
            if m and value is not None:
                idx = int(m.group(1))
                connected[key] = (value, idx)

        if not connected:
            _logger.debug(f"[{unique_id}] No inputs connected, returning None")
            return (None, 0)

        # Is the dropdown participating in the resolution chain?
        dropdown_active = select not in (self.NONE_SELECTION, self.NO_CONNECTIONS)

        # Resolve negative override to Nth-from-last connected input
        # -1 = last connected, -2 = second-to-last, etc.
        if select_override < 0:
            sorted_connected = sorted(connected.keys())
            neg_idx = abs(select_override)
            if neg_idx <= len(sorted_connected):
                resolved_key = sorted_connected[-neg_idx]
                value, idx = connected[resolved_key]
                _logger.debug(
                    f"[{unique_id}] Negative override {select_override} "
                    f"resolved to {resolved_key} (index {idx})"
                )
                return (value, idx)
            _logger.debug(
                f"[{unique_id}] Negative override {select_override} out of range "
                f"({len(sorted_connected)} connected), falling through"
            )
            # Fall through to dropdown / mode like a positive miss

        # Step 1: Try override (positive)
        if select_override > 0:
            override_key = f"input_{select_override:02d}"
            if override_key in connected:
                value, idx = connected[override_key]
                _logger.debug(f"[{unique_id}] Override selected {override_key} (index {idx})")
                return (value, idx)
            if dropdown_active:
                _logger.debug(f"[{unique_id}] Override {override_key} unavailable, trying dropdown")
            else:
                _logger.debug(f"[{unique_id}] Override {override_key} unavailable, applying {mode}")

        # Step 2: Dropdown selection (skipped when select is "(none)")
        if dropdown_active and select in connected:
            value, idx = connected[select]
            _logger.debug(f"[{unique_id}] Dropdown selected {select} (index {idx})")
            return (value, idx)

        # "Requested" for sequential scan position:
        # override key if set, dropdown value if active, else None
        if select_override > 0:
            requested = f"input_{select_override:02d}"
        elif select_override < 0:
            # Negative override missed — no meaningful position for sequential
            requested = None
        elif dropdown_active:
            requested = select
        else:
            requested = None

        # Step 3: Apply mode fallback
        _logger.debug(
            f"[{unique_id}] Requested '{requested}' unavailable, "
            f"applying {mode} fallback"
        )

        if mode == "strict":
            _logger.debug(f"[{unique_id}] Strict mode: no fallback")
            return (None, 0)

        if mode == "priority":
            # First non-None by slot position (top to bottom)
            for key in sorted(connected.keys()):
                value, idx = connected[key]
                _logger.debug(f"[{unique_id}] Priority fallback: {key} (index {idx})")
                return (value, idx)
            return (None, 0)

        if mode == "sequential":
            # Build full slot range including gaps (disconnected slots)
            # ComfyUI omits disconnected inputs from kwargs, so we reconstruct
            # the complete range from max(connected, requested) slot numbers
            all_slots = self._build_full_slot_range(connected, requested)
            if requested is not None and requested in all_slots:
                start_pos = all_slots.index(requested)
            else:
                start_pos = 0
            # When requested is None (no dropdown, no override), scan from top
            # including position 0; otherwise skip the requested position
            start_offset = 0 if requested is None else 1
            for i in range(start_offset, len(all_slots)):
                candidate = all_slots[(start_pos + i) % len(all_slots)]
                if candidate in connected:
                    value, idx = connected[candidate]
                    _logger.debug(
                        f"[{unique_id}] Sequential fallback: {candidate} (index {idx})"
                    )
                    return (value, idx)
            return (None, 0)

        # Unknown mode — treat as priority
        _logger.warning(f"[{unique_id}] Unknown mode '{mode}', using priority")
        for key in sorted(connected.keys()):
            value, idx = connected[key]
            return (value, idx)
        return (None, 0)


# ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "DazzleSwitch": DazzleSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DazzleSwitch": "Dazzle Switch (DazzleNodes)",
}
