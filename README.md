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
| Input order matters | Yes (top wins) | No (user picks) |
| Renaming slots | Not used | Core feature (labels in dropdown) |
| Programmatic control | None | INT override input |
| Chaining | Not possible | Chain INT to drive multiple switches |

## Features

- **Dropdown Selection**: Choose which input to route via a labeled dropdown
- **Type-Agnostic**: Works with MODEL, CLIP, LATENT, IMAGE, MASK, STRING, or any other type
- **Named Inputs**: Rename input slots (right-click → Rename) and see names in the dropdown
- **INT Override**: `select_override` input (0=dropdown, 1-5=programmatic selection)
- **Cascading**: Wire one INT value to multiple DazzleSwitch nodes for single-edit cascade
- **Auto-Fallback**: If selected input disconnects, auto-selects first remaining connected
- **DazzleNodes Compatible**: Works standalone or as part of the DazzleNodes collection

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
| select_override | INT | No | Programmatic override (0=dropdown, 1-5=select input) |
| input_01–input_05 | Any | No | Data inputs — connect any type |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| output | Any | The selected input value |
| selected_index | INT | 1-based index of which input was selected (0 if none) |

### Selection Priority

1. **INT override > 0**: Uses `input_{override}` if connected
2. **Override fails or is 0**: Uses dropdown widget selection
3. **Dropdown target disconnected**: Falls back to first connected input
4. **Nothing connected**: Returns `(None, 0)`

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
Wire one INT to drive multiple switches simultaneously:
```
[INT Widget: 2] → select_override → [DazzleSwitch A] (selects input_02)
                → select_override → [DazzleSwitch B] (selects input_02)
                → select_override → [DazzleSwitch C] (selects input_02)
```

## Debug Logging

```bash
# Enable debug output
DS_DEBUG=1 python main.py
```

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

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test changes in ComfyUI
4. Submit a pull request

Like the project?

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/djdarcy)

## Acknowledgements

Part of the [DazzleNodes](https://github.com/DazzleNodes) collection.

Inspired by:
- [rgthree-comfy](https://github.com/rgthree/rgthree-comfy) Any Switch node
- [ComfyUI-PreviewBridgeExtended](https://github.com/DazzleNodes/ComfyUI-PreviewBridgeExtended) (project template)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
