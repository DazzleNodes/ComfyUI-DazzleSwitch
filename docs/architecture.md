# DazzleSwitch Architecture

## Overview

DazzleSwitch is a ComfyUI custom node with two components:

1. **Python backend** (`py/node.py`) — Registered with ComfyUI as the `DazzleSwitch` node class. Handles execution: receives the selected input name, resolves it, and passes the value through.
2. **JavaScript extension** (`web/main.js`) — Runs in the ComfyUI browser frontend. Manages dynamic input slots, the dropdown widget, type detection, label caching, and the active slot highlight.

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (LiteGraph)                  │
│                                                         │
│  [Connect input] → onConnectionsChange                  │
│       ↓                                                 │
│  scheduleStabilize (64ms debounce)                      │
│       ↓                                                 │
│  stabilizeInputs:                                       │
│    1. addBufferInputIfNeeded (grow)                     │
│    2. removeUnusedInputsFromEnd (shrink)                │
│    3. watchInputLabels (install rename watchers)        │
│    4. updateSelectWidget (rebuild dropdown)             │
│    5. updateOutputType (detect + show type)             │
│       ↓                                                 │
│  [Queue Prompt]                                         │
│       ↓                                                 │
│  serializeValue: maps display label → internal name     │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP POST (prompt)
                           ↓
┌─────────────────────────────────────────────────────────┐
│                    Python (Server)                      │
│                                                         │
│  DazzleSwitch.switch(select="input_02",                 │
│                      select_override=0,                 │
│                      input_01=<tensor>, ...)            │
│       ↓                                                 │
│  1. Build connected dict from kwargs (regex)            │
│  2. Check select_override > 0 → use that input          │
│  3. Else use dropdown value (select param)              │
│  4. Return (value, 1-based-index)                       │
└─────────────────────────────────────────────────────────┘
```

## Python Backend

### Key Classes

**`AnyType(str)`** — A string subclass where `__ne__` always returns `False`. ComfyUI validates connections using `!=`; by never reporting inequality, this type accepts connections from any other type.

**`FlexibleOptionalInputType(dict)`** — A dict subclass where `__contains__` always returns `True` and `__getitem__` returns a flexible type tuple for unknown keys. This tricks ComfyUI's server-side validation into accepting dynamically-added input slots (input_04, input_05, etc.) that aren't declared in `INPUT_TYPES()`.

**`DazzleSwitch`** — The node class. `INPUT_TYPES` declares 3 initial optional inputs plus `select_override`. The `switch()` method receives all connected inputs as `**kwargs`, iterates them with a regex pattern (`^input_(\d{2})$`), and resolves the selection.

### VALIDATE_INPUTS Bypass

The `select` dropdown widget is dynamically populated by JS. The server only sees the static `["(none connected)"]` list from `INPUT_TYPES()`. Without `VALIDATE_INPUTS` returning `True` unconditionally, any real dropdown selection would fail server-side combo validation.

## JavaScript Extension

### Dynamic Input Slots

Inputs grow and shrink automatically:
- **Grow**: When the last `input_XX` slot gets connected, a new empty slot is appended (up to input_99)
- **Shrink**: Trailing disconnected slots beyond the minimum (3) are removed
- Both operations are debounced at 64ms to prevent flicker during rapid connection changes

### Label Cache

`node._dsLabelCache` is a dictionary that maps internal names (e.g., `"input_03"`) to user-assigned labels. When a slot is removed (shrink), its label is cached. When a slot with the same name is recreated (grow), the label is restored. This means users can rename `input_05` to "LoRA Style", disconnect it, and when it reappears later, it still says "LoRA Style".

### Name Map and Serialization

The dropdown shows display labels (user-renamed slot names), but Python needs internal names (`input_01`, `input_02`, etc.). The `_dsNameMap` dictionary maps display labels to internal names. The `serializeValue` override on the select widget translates display → internal before sending to the server.

### Active Slot Highlight

The `onDrawForeground` hook draws a semi-transparent green tint (`rgba(91, 189, 91, 0.15)`) on the currently selected input slot. It uses `node.getConnectionPos(true, slotIndex, pos)` for accurate positioning, converting absolute coordinates to node-relative coordinates for drawing.

The highlight auto-hides when:
- The node is collapsed
- Canvas zoom is below 0.5x (too small to see)

## Entry Point

`__init__.py` handles:
1. **Debug logging** — Enabled via `DS_DEBUG=1` environment variable
2. **Dual-loading guard** — A `sys`-level sentinel (`_dazzle_switch_loaded`) detects when the node is loaded both standalone and via DazzleNodes. The duplicate load's `WEB_DIRECTORY` is set to `None` to prevent double JS registration.
3. **Exports** — `NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`, `WEB_DIRECTORY`
