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

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "select": (["(none connected)"], {
                    "default": "(none connected)",
                    "tooltip": "Choose which connected input to route to output. "
                               "Options update automatically based on connections.",
                }),
            },
            "optional": FlexibleOptionalInputType(any_type, {
                "select_override": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 50,
                    "tooltip": "Programmatic override: 0 = use dropdown, "
                               "1+ = select that input number directly. "
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

    def switch(self, select="(none connected)", select_override=0,
               unique_id=None, **kwargs):
        """Route the selected input to output.

        Selection priority:
        1. select_override > 0 -> use input_{override:02d} if connected
        2. select_override == 0 or override target not connected -> use dropdown
        3. Dropdown target not connected -> first connected input (fallback)
        4. Nothing connected -> (None, 0)
        """
        # Build dict of connected (non-None) inputs with their indices
        # Dynamic: iterates all input_XX keys from kwargs, not a hardcoded range
        connected = {}
        for key, value in kwargs.items():
            m = self._INPUT_RE.match(key)
            if m and value is not None:
                idx = int(m.group(1))
                connected[key] = (value, idx)

        if not connected:
            _logger.debug(f"[{unique_id}] No inputs connected, returning None")
            return (None, 0)

        # Priority 1: INT override
        if select_override > 0:
            override_key = f"input_{select_override:02d}"
            if override_key in connected:
                value, idx = connected[override_key]
                _logger.debug(f"[{unique_id}] Override selected {override_key} (index {idx})")
                return (value, idx)
            else:
                _logger.debug(
                    f"[{unique_id}] Override {select_override} not connected, "
                    f"falling back to dropdown"
                )

        # Priority 2: Dropdown selection
        # The JS sends the internal input name (e.g., "input_01") via the name map
        if select in connected:
            value, idx = connected[select]
            _logger.debug(f"[{unique_id}] Dropdown selected {select} (index {idx})")
            return (value, idx)

        # Priority 3: Fallback to first connected input
        first_key = next(iter(connected))
        value, idx = connected[first_key]
        _logger.debug(
            f"[{unique_id}] Dropdown target '{select}' not connected, "
            f"falling back to {first_key} (index {idx})"
        )
        return (value, idx)


# ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "DazzleSwitch": DazzleSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DazzleSwitch": "Dazzle Switch (DazzleNodes)",
}
