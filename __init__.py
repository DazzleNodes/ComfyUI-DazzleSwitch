"""
ComfyUI Dazzle Switch - DazzleNodes Custom Node
Smart switch node with dropdown-based input selection and INT override.

Part of the DazzleNodes collection - standalone ComfyUI custom nodes.
"""

import logging
import os
import sys

# Configure module logger
_logger = logging.getLogger("DazzleSwitch")

# Enable debug logging via environment variable: DS_DEBUG=1
if os.environ.get('DS_DEBUG', '').lower() in ('1', 'true', 'yes'):
    _logger.setLevel(logging.DEBUG)
    if not _logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setFormatter(logging.Formatter('[%(name)s] %(levelname)s: %(message)s'))
        _logger.addHandler(_handler)

# =====================================================
# DUAL-LOADING DETECTION
# Prevents issues when DazzleSwitch is installed both
# as a standalone node AND inside DazzleNodes.
# Uses a sys-level sentinel (shared across all module
# namespaces) to detect the second load.
# =====================================================
_DS_SENTINEL = '_dazzle_switch_loaded'
_is_duplicate_load = hasattr(sys, _DS_SENTINEL)

if _is_duplicate_load:
    _first_path = getattr(sys, _DS_SENTINEL)
    _this_path = os.path.dirname(os.path.abspath(__file__))
    print(f"[DazzleSwitch] WARNING: Duplicate installation detected!")
    print(f"[DazzleSwitch]   Already loaded from: {_first_path}")
    print(f"[DazzleSwitch]   Skipping this copy:  {_this_path}")
    print(f"[DazzleSwitch]   Fix: Remove one installation (standalone symlink or DazzleNodes submodule).")
else:
    setattr(sys, _DS_SENTINEL, os.path.dirname(os.path.abspath(__file__)))

from .py import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .version import __version__

# Tell ComfyUI where to find our JavaScript files
# Disabled on duplicate loads to prevent double JS extension registration
WEB_DIRECTORY = None if _is_duplicate_load else "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

# Display version info on load
if _is_duplicate_load:
    print(f"[DazzleSwitch] Duplicate skipped v{__version__} (JS disabled)")
else:
    print(f"[DazzleSwitch] Loaded v{__version__}")
