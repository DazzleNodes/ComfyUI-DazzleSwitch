# Contributing to ComfyUI-DazzleSwitch

Thank you for considering contributing to Dazzle Switch!

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct.
By participating in this project you agree to abide by its terms.

## Development Setup

### Prerequisites

- ComfyUI installation (for testing)
- Python 3.10+
- Git

### Getting Started

```bash
# Clone the repository
git clone https://github.com/DazzleNodes/ComfyUI-DazzleSwitch.git
cd ComfyUI-DazzleSwitch

# Install git hooks for automatic version tracking
bash scripts/install-hooks.sh

# Symlink into ComfyUI for live development
cd /path/to/ComfyUI/custom_nodes
ln -s /path/to/ComfyUI-DazzleSwitch ComfyUI-DazzleSwitch
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Or use pytest directly
pytest tests/ -v
```

## Project Structure

```
├── __init__.py          # ComfyUI entry point, dual-loading guard
├── py/
│   ├── __init__.py      # Re-exports NODE_CLASS_MAPPINGS
│   └── node.py          # DazzleSwitch node class (Python backend)
├── web/
│   └── main.js          # JS extension (dynamic inputs, dropdown, type detection, UI)
├── version.py           # Semantic version (updated by git hooks)
├── tests/               # Test suites
│   └── one-offs/        # One-off diagnostic/proof-of-concept scripts
├── docs/                # Detailed documentation
└── scripts/             # Git hooks, version management
```

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/DazzleNodes/ComfyUI-DazzleSwitch/issues) first
2. Include your ComfyUI version and Python version
3. Provide steps to reproduce the issue
4. Include console output (enable debug logging with `DS_DEBUG=1`)

### Suggesting Enhancements

Open an issue describing the feature, the use case, and how it would work from a user's perspective.

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Test in ComfyUI (connect inputs, test dropdown, test override, test disconnect/reconnect)
5. Run `python run_tests.py` to verify tests pass
6. Submit a pull request

## Code Style

### Python

- Follow PEP 8
- Use type hints where practical
- Prefix private methods with `_`
- Use `_logger.debug()` for debug output (controlled by `DS_DEBUG` env var)

### JavaScript

- The extension is a single `web/main.js` file — keep it that way unless there's strong reason to split
- Use `const` over `let` where possible
- Guard against missing nodes/widgets (ComfyUI loads extensions before nodes are fully initialized)
- Use `WeakMap` for per-node state that should be garbage collected

### Key Patterns

- **AnyType**: `class AnyType(str)` with `__ne__` returning `False` — matches all ComfyUI types
- **FlexibleOptionalInputType**: Dict subclass that accepts any key — enables dynamic input slots
- **Debounced stabilize**: 64ms debounce on connection changes prevents flicker during rapid operations
- **Label cache**: `node._dsLabelCache` stores slot labels before removal, restores on recreation

## License

By contributing, you agree that your contributions will be licensed under the [GNU General Public License v3.0](LICENSE).
