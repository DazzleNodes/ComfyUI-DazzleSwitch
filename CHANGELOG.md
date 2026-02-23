# Changelog

All notable changes to ComfyUI Dazzle Switch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
