# DazzleNodes - Dazzle Switch
# Node implementations
#
# This package provides the DazzleSwitch node for ComfyUI.
# Single module: node.py handles all switch logic.

from .node import (
    DazzleSwitch,
    FlexibleOptionalInputType,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

__all__ = [
    'DazzleSwitch',
    'FlexibleOptionalInputType',
    'NODE_CLASS_MAPPINGS',
    'NODE_DISPLAY_NAME_MAPPINGS',
]
