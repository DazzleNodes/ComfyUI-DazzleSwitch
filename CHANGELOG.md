# Changelog

All notable changes to ComfyUI Dazzle Switch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0-alpha] - 2026-02-24

### Added
- Fallback modes: `priority` (rgthree-style top-down), `strict` (no fallback), `sequential` (next slot with wrap-around)
- `(none)` dropdown option: skip dropdown step entirely, let mode decide (6-behavior matrix with modes)
- Negative indexing: `select_override = -1` selects last connected input, `-2` second-to-last, etc.
- Widget dimming: `select_override` visually dims at 35% opacity when value is 0 (inactive)
- Custom draw method for select_override matching ComfyUI's BaseSteppedWidget rendering
- 31 new tests: 12 for (none)+mode matrix, 8 for negative indexing, 11 for sequential gap-awareness (86 total)
- README: resolution chain docs, fallback mode table, (none) option behavior matrix

### Changed
- `select_override` range expanded from `0..50` to `-50..50` for negative indexing
- Resolution chain: override (negative → positive) → dropdown (unless "(none)") → mode fallback
- Version bump: 0.3.1 → 0.4.0 across version.py, pyproject.toml, setup.py

### Fixed
- Sequential mode: correctly scans forward through disconnected slot gaps (ComfyUI omits disconnected inputs from kwargs)
- `_build_full_slot_range()` reconstructs complete slot topology so sequential wrap-around respects physical slot positions

### Technical Details
- `dropdown_active` flag skips dropdown step when `(none)` selected (clean separation of concerns)
- Negative override resolved against `sorted(connected.keys())` before positive check
- `_build_full_slot_range()`: builds `[input_01..input_N]` from max(connected, requested) for gap-aware sequential scan
- `installOverrideDim()`: assigns `.draw` method with alpha control, matches capsule + arrows + text rendering
- `DISABLED_WIDGET_ALPHA = 0.35` for visible-but-dimmed appearance (arrows and value still shown)

## [0.3.1-alpha] - 2026-02-23

### Added
- Slot reordering: right-click input slots → Move Up / Move Down to rearrange positions
- Connections, labels, and override indices follow the slot during reorder (swap-and-rename)
- README: cascading selection guide explaining `selected_index` → `select_override` workflow
- README: slot alignment walkthrough with before/after examples
- Link to [#7](https://github.com/DazzleNodes/ComfyUI-DazzleSwitch/issues/7) for future named channels roadmap

### Technical Details
- `moveInputSlot()`: array splice + sequential rename + label cache re-key + link patching
- `getSlotMenuOptions` override adds context menu items for input_XX slots only
- Link integrity maintained via rgthree-proven `target_slot` patching pattern
- Stabilize cycle re-triggered after reorder (dropdown, type detection, label watchers rebuild)

## [0.3.0-alpha] - 2026-02-23

### Added
- Label cache: slot labels (user renames) preserved across disconnect/reconnect cycles
- Active slot highlight: semi-transparent green tint on the currently selected input slot
- DazzleNodes collection integration: loads via DazzleNodes or standalone with dual-loading guard
- Display name updated to "Dazzle Switch (DazzleNodes)" for searchability in node browser

### Changed
- Visual highlight uses `onDrawForeground` with `getConnectionPos()` for accurate slot positioning
- Label cache stores/restores unconditionally (no type gating)

### Technical Details
- `node._dsLabelCache` dictionary caches labels before slot removal, restores on recreation
- Active highlight: `rgba(91, 189, 91, 0.15)` fill, auto-hides when collapsed or zoomed out (<0.5x)
- DazzleNodes web sync: copies JS files from `nodes/*/web/` to `DazzleNodes/web/` with hash-based cache
- Pre-commit hook regex patterns fixed (escaped dots, anchored patterns)

## [0.2.0-alpha] - 2026-02-23

### Added
- Dynamic input expansion: slots grow when last input is connected, shrink when trailing slots disconnect (minimum 3)
- `FlexibleOptionalInputType` for accepting undeclared dynamic inputs (input_04, input_05, ..., input_99)
- Type detection via LiteGraph connection graph walking (follows through Reroute and chained DazzleSwitches)
- Output type label shows detected type of selected input (e.g., "MODEL", "IMAGE" instead of "*")
- Debounced stabilize cycle (64ms) prevents flicker during rapid connect/disconnect operations
- Label watcher via Object.defineProperty for live dropdown updates on slot rename
- `VALIDATE_INPUTS` bypass for server-side combo validation of dynamic dropdown values
- `run_tests.py` test runner integrated with pre-push git hook
- 36 one-off tests (18 new Phase 2 tests: FlexibleOptionalInputType, dynamic kwargs, regex edge cases, VALIDATE_INPUTS)
- Example workflow: `examples/DazzleSwitch-Test.json`

### Changed
- Reduced initial input slots from 5 to 3 (dynamic expansion replaces fixed count)
- `switch()` now uses regex-based kwargs iteration instead of hardcoded `range(1, 6)`
- Dropdown preserves user selection when selected input is disconnected (no auto-fallback)
- `onConnectionsChange` now triggers debounced stabilize instead of direct dropdown rebuild

### Technical Details
- Adapted rgthree patterns (FlexibleOptionalInputType, stabilize, graph walking) with mixed-type awareness
- Input slots stay `*` always (mixed types supported, unlike rgthree which sets all to same type)
- Only selected input's type is detected (not all inputs)
- WeakMap-based per-node debounce timers (GC-friendly)
- Graph walk: max 10 hops, visited set prevents infinite loops

## [0.1.0-alpha] - 2026-02-22

### Added
- Initial release of DazzleSwitch node
- 5 optional AnyType inputs (input_01 through input_05) — route any ComfyUI data type
- `select` dropdown widget dynamically populated by JS with connected input names
- `select_override` INT input for programmatic cascading (0 = use dropdown, 1-5 = select input)
- Dual-loading detection guard (same pattern as PreviewBridgeExtended)
- DazzleNodes integration with import.meta.url depth detection for JS compatibility
- Outputs: `output` (selected value, AnyType) + `selected_index` (1-based INT)

### Technical Details
- AnyType pattern (`__ne__` returning False) for universal type matching
- JS extension rebuilds dropdown on `onConnectionsChange` and `onConfigure`
- Name map serialization: dropdown shows display labels, Python receives internal names
- Templated from ComfyUI-PreviewBridgeExtended project structure
- Part of DazzleNodes collection
