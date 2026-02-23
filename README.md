# ComfyUI Dazzle Switch
### *Pick Your Noodle*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub release](https://img.shields.io/github/v/release/DazzleNodes/ComfyUI-DazzleSwitch?include_prereleases&label=version)](https://github.com/DazzleNodes/ComfyUI-DazzleSwitch/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Smart switch node for ComfyUI. Name your inputs, pick from a dropdown, no more noodle spaghetti.

## Overview

DazzleSwitch routes any ComfyUI data type through a user-selected dropdown instead of requiring noodle rearrangement. Connect multiple inputs, name them, and select which one passes through — all from a dropdown widget. An INT override input enables programmatic cascading: one upstream value drives multiple switches.

### Comparison with rgthree Any Switch

| | rgthree Any Switch | DazzleSwitch |
|---|---|---|
| Selection | First non-None (implicit) | Dropdown widget (explicit) |
| Input count | Fixed slots | Dynamic (grows on connect, shrinks on disconnect) |
| Input order matters | Yes (top wins) | No (user picks) |
| Renaming slots | Not used | Core feature (labels in dropdown) |
| Label persistence | N/A | Labels survive disconnect/reconnect |
| Type detection | None | Shows detected type of selected input |
| Programmatic control | None | INT override input |
| Chaining | Not possible | Chain INT to drive multiple switches |
| Slot reordering | Not supported | Right-click Move Up/Down |
| Active indicator | None | Green tint on selected slot |

## Features

- **Dropdown Selection**: Choose which input to route via a labeled dropdown
- **Dynamic Inputs**: Slots grow when you connect the last one, shrink when trailing slots disconnect (minimum 3)
- **Type-Agnostic**: Works with MODEL, CLIP, LATENT, IMAGE, MASK, STRING, or any other type
- **Type Detection**: Output label shows the detected type of the selected input (e.g., "MODEL" instead of "*")
- **Named Inputs**: Rename input slots (right-click → Rename) and see names in the dropdown
- **Label Cache**: Slot labels persist across disconnect/reconnect cycles — no need to re-rename
- **Active Slot Highlight**: Semi-transparent green tint shows which input is currently selected
- **Slot Reordering**: Right-click → Move Up/Down to rearrange input positions for [cascading alignment](https://github.com/DazzleNodes/ComfyUI-DazzleSwitch/issues/7)
- **INT Override**: `select_override` input (0=dropdown, 1+=programmatic selection)
- **Cascading**: Wire one INT value to multiple DazzleSwitch nodes for single-edit cascade
- **DazzleNodes Compatible**: Works standalone or as part of the [DazzleNodes](https://github.com/DazzleNodes) collection

## Prerequisites

- ComfyUI installation
- Python 3.10+

## Installation

### Git Clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/DazzleNodes/ComfyUI-DazzleSwitch.git
```

Then restart ComfyUI or use **Manager → Refresh Node Definitions**.

### Manual Installation

1. Download the [latest release](https://github.com/DazzleNodes/ComfyUI-DazzleSwitch/releases)
2. Extract to `ComfyUI/custom_nodes/ComfyUI-DazzleSwitch/`
3. Restart ComfyUI
4. Find the node in: **DazzleNodes → Dazzle Switch**

## Usage

### Inputs

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| select | Dropdown | Yes | Which connected input to route to output |
| select_override | INT | No | Programmatic override (0=dropdown, 1+=select input by number) |
| input_01, input_02, ... | Any | No | Data inputs — connect any type. New slots appear as you connect. |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| output | Any | The selected input value (type label shows detected type) |
| selected_index | INT | 1-based index of which input was selected (0 if none) |

### Selection Priority

1. **INT override > 0**: Uses `input_{override}` if connected
2. **Override fails or is 0**: Uses dropdown widget selection
3. **Nothing connected**: Returns `(None, 0)`

### Common Use Cases

#### A/B Switching
Connect two models/images/LoRAs and pick from the dropdown:
```
[Model A] → input_01 ("Base Model")
[Model B] → input_02 ("Fine-tuned")
                         ↓ select: "Base Model"
                    [DazzleSwitch] → output → [KSampler]
```

#### Cascading Selection
Wire one switch's `selected_index` to another's `select_override` so they change together:
```
[DazzleSwitch A] ─ selected_index → select_override ─ [DazzleSwitch B]
```

When you pick "Style B" (position 2) on Switch A, Switch B automatically selects its position 2 as well. This lets you control multiple switches from a single dropdown.

You can also drive multiple switches from a plain INT widget:
```
[INT Widget: 2] → select_override → [DazzleSwitch A] (selects position 2)
                → select_override → [DazzleSwitch B] (selects position 2)
                → select_override → [DazzleSwitch C] (selects position 2)
```

#### Aligning Positions Across Chained Switches

When chained switches have different inputs, the same position number may mean different things:

```
Switch A:                        Switch B:
  1: "Reference Image"            1: "Toggle"         ← wrong match!
  2: "Alt Image"                  2: "Inpaint Mask"
                                  3: "Flux Prompt"
                                  4: "Reference Image" ← this is what you want at position 1
```

To fix this, **right-click any input slot** and use **Move Up / Move Down** to reorder it. Moving "Reference Image" to position 1 on Switch B makes the cascade work correctly:

```
Switch B (after reorder):
  1: "Reference Image"  ← now matches Switch A position 1
  2: "Toggle"
  3: "Inpaint Mask"
  4: "Flux Prompt"
```

Connections, labels, and override indices all follow the slot when it moves — no need to disconnect and reconnect noodles.

> **Future: Named Channels** — Slot reordering is a manual workaround. A future release will add string-based cascading (`selected_key` / `select_key_override`) so switches can match by label name instead of position, eliminating the need to align slot order entirely. See [#7](https://github.com/DazzleNodes/ComfyUI-DazzleSwitch/issues/7) for the design discussion.

#### Dynamic Multi-Input Routing
Connect as many inputs as you need — the node grows automatically:
```
[LoRA 1] → input_01 ("Style A")
[LoRA 2] → input_02 ("Style B")
[LoRA 3] → input_03 ("Style C")    ← connecting here creates input_04
[LoRA 4] → input_04 ("Style D")    ← connecting here creates input_05
```

## Debug Logging

```bash
# Enable debug output
DS_DEBUG=1 python main.py
```

## Documentation

Detailed documentation is available in the [`docs/`](docs/) folder:

- [Architecture](docs/architecture.md) — Node design, JS extension, Python backend, data flow
- [Type Detection](docs/type-detection.md) — Graph walking algorithm for connection type inference
- [DazzleNodes Integration](docs/dazzlenodes-integration.md) — Dual loading, web sync, development setup

## Development

This project uses Git-RepoKit hooks for automatic version tracking.

```bash
git clone https://github.com/DazzleNodes/ComfyUI-DazzleSwitch.git
cd ComfyUI-DazzleSwitch

# Install hooks for version tracking
bash scripts/install-hooks.sh

# Symlink to ComfyUI for development
cd /path/to/ComfyUI/custom_nodes
ln -s /path/to/ComfyUI-DazzleSwitch ComfyUI-DazzleSwitch
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

Like the project?

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/djdarcy)

## Acknowledgements

Part of the [DazzleNodes](https://github.com/DazzleNodes) collection.

Inspired by:
- [rgthree-comfy](https://github.com/rgthree/rgthree-comfy) Any Switch node
- [ComfyUI-PreviewBridgeExtended](https://github.com/DazzleNodes/ComfyUI-PreviewBridgeExtended) (project template)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
