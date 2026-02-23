# DazzleNodes Integration

## Overview

DazzleSwitch can run in two modes:
1. **Standalone** — Installed directly in `ComfyUI/custom_nodes/ComfyUI-DazzleSwitch/`
2. **DazzleNodes collection** — Loaded as a sub-node via the [DazzleNodes](https://github.com/DazzleNodes) parent package

Both modes produce identical behavior. The dual-loading guard ensures that if both are present, only one instance registers its JS extension.

## How DazzleNodes Loads Sub-Nodes

DazzleNodes' `__init__.py` scans its `nodes/` directory for sub-nodes. Each sub-node is a directory (or symlink) containing a standard ComfyUI custom node structure:

```
DazzleNodes/
├── __init__.py              # Parent loader
├── nodes/
│   ├── dazzle-switch/       # Symlink or submodule → ComfyUI-DazzleSwitch
│   ├── preview-bridge-ext/  # Another sub-node
│   └── ...
└── web/                     # Synced JS files (generated)
```

DazzleNodes calls `load_node_module("dazzle-switch", "Dazzle Switch")` which imports the sub-node's `__init__.py` and collects its `NODE_CLASS_MAPPINGS`.

## Dual-Loading Guard

When DazzleSwitch is installed both standalone and via DazzleNodes, ComfyUI would load it twice. The guard uses a `sys`-level sentinel:

```python
_DS_SENTINEL = '_dazzle_switch_loaded'
_is_duplicate_load = hasattr(sys, _DS_SENTINEL)

if _is_duplicate_load:
    # Print warning, set WEB_DIRECTORY = None
else:
    setattr(sys, _DS_SENTINEL, ...)
    # Normal load, WEB_DIRECTORY = "./web"
```

The first load wins. The second load's `WEB_DIRECTORY` is set to `None` so its JS extension doesn't double-register.

## Web File Sync

ComfyUI's web server only serves JS from `custom_nodes/<node>/web/`. Since DazzleNodes loads sub-nodes from `nodes/*/`, JS files in `nodes/dazzle-switch/web/` wouldn't be served directly.

DazzleNodes solves this with `scripts/sync_web_files.py`:

1. Scans `nodes/*/web/` for `.js` files
2. Copies them to `DazzleNodes/web/<node-name>/`
3. Uses MD5 hash-based caching (`.sync_hash`) to skip unnecessary copies
4. Runs on ComfyUI startup via DazzleNodes' `__init__.py`

The sync script uses `Path(__file__).resolve().parent.parent` to resolve paths relative to the script location, not the working directory. This ensures it works regardless of where ComfyUI is started from.

### Forcing a re-sync

```bash
python scripts/sync_web_files.py --force
```

## Development Setup

For development, use a symlink (or Windows directory junction) so changes in the DazzleSwitch repo are immediately available to DazzleNodes:

```bash
# Linux/macOS
ln -s /path/to/ComfyUI-DazzleSwitch /path/to/DazzleNodes/nodes/dazzle-switch

# Windows (directory junction, requires admin or dev mode)
mklink /J "C:\path\to\DazzleNodes\nodes\dazzle-switch" "C:\path\to\ComfyUI-DazzleSwitch"
```

After editing JS files, run the web sync to copy updated files:

```bash
python /path/to/DazzleNodes/scripts/sync_web_files.py --force
```

Then refresh the browser (Ctrl+F5) to pick up the new JS.

## JS Import Compatibility

The JS extension uses `import.meta.url` with depth detection to resolve imports correctly in both standalone and nested modes:

```javascript
const currentPath = import.meta.url;
const urlParts = new URL(currentPath).pathname.split('/').filter(p => p);
const depth = urlParts.length;
const prefix = '../'.repeat(depth);

const appModule = await import(`${prefix}scripts/app.js`);
```

- **Standalone**: URL is `/extensions/ComfyUI-DazzleSwitch/main.js` → depth determines correct `../` prefix to reach `/scripts/app.js`
- **DazzleNodes**: URL is `/extensions/DazzleNodes/ComfyUI-DazzleSwitch/main.js` → deeper path, more `../` prefixes
