# Changelog

All notable changes to ComfyUI Dazzle Switch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
