"""
DazzleSwitch - Smart switch node with dropdown-based input selection.

Routes any ComfyUI data type through a user-selected dropdown,
with programmatic INT override for cascading workflows.
"""

import logging

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


class DazzleSwitch:
    """Smart switch node — route any input via dropdown selection or INT override.

    Features:
    - 5 optional typed-as-any inputs (input_01 through input_05)
    - Dropdown widget dynamically populated by JS with connected input names
    - INT select_override for programmatic cascading (0 = use dropdown)
    - Outputs: selected value + 1-based index of which input was selected
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
            "optional": {
                "select_override": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 50,
                    "tooltip": "Programmatic override: 0 = use dropdown, "
                               "1-5 = select input_01 through input_05. "
                               "Enables cascading selection from upstream.",
                }),
                "input_01": (any_type, {}),
                "input_02": (any_type, {}),
                "input_03": (any_type, {}),
                "input_04": (any_type, {}),
                "input_05": (any_type, {}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = (any_type, "INT")
    RETURN_NAMES = ("output", "selected_index")
    FUNCTION = "switch"
    CATEGORY = "DazzleNodes"
    OUTPUT_NODE = False

    def switch(self, select="(none connected)", select_override=0,
               unique_id=None, **kwargs):
        """Route the selected input to output.

        Selection priority:
        1. select_override > 0 → use input_{override:02d} if connected
        2. select_override == 0 or override target not connected → use dropdown
        3. Dropdown target not connected → first connected input (fallback)
        4. Nothing connected → (None, 0)
        """
        # Build dict of connected (non-None) inputs with their indices
        connected = {}
        for i in range(1, 6):
            key = f"input_{i:02d}"
            if key in kwargs and kwargs[key] is not None:
                connected[key] = (kwargs[key], i)

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
    "DazzleSwitch": "Dazzle Switch",
}
