# Type Detection via Graph Walking

## Problem

DazzleSwitch uses `AnyType("*")` for all inputs and outputs, which means ComfyUI shows `*` as the type everywhere. This gives users no indication of what data type is actually flowing through the node.

## Solution

The JS extension walks the connection graph backward from the selected input to find the first non-`*` output type. The detected type is then shown as the output slot's label (e.g., "MODEL" instead of "output").

## Algorithm: `followConnectionUntilType`

```
followConnectionUntilType(graph, node, slotIndex, visited, depth):
    if depth >= 10: return "*"                    # Max recursion depth
    if slot has no link: return "*"               # Not connected
    if link already visited: return "*"           # Infinite loop prevention

    mark link as visited
    find source node and output slot via link

    if source output type != "*":
        return source output type                 # Found a real type

    # Source is also "*" — recurse into source's inputs
    for each connected input on source node:
        result = followConnectionUntilType(source, inputIndex, ...)
        if result != "*": return result

    return "*"                                    # All wildcards
```

### What it handles

| Scenario | Behavior |
|----------|----------|
| Direct connection (KSampler → DazzleSwitch) | Returns "LATENT" from KSampler's output type |
| Through Reroute node | Reroute outputs `*`, so recursion continues to the node before Reroute |
| Through chained DazzleSwitches | DazzleSwitch also outputs `*`, so recursion walks through to the original source |
| Circular connections | `visited` set prevents infinite loops |
| Very deep chains | Max depth of 10 hops stops runaway recursion |
| Disconnected input | Returns `*` immediately |

### When it runs

Type detection runs during `stabilizeInputs()`, which is triggered (debounced at 64ms) by:
- Connection changes (`onConnectionsChange`)
- Slot label changes (via `Object.defineProperty` watcher)
- Widget value changes

### Output type update

`updateOutputType(node, type)` sets the first output slot's type and label:
- Detected type (e.g., `"MODEL"`) → label shows `"MODEL"`
- No detection (`"*"`) → label shows `"output"` (the default)

This is a visual-only change — it doesn't affect ComfyUI's type validation (which is already bypassed by `AnyType`).

## Limitations

- Only detects the type of the **currently selected** input, not all inputs
- If the entire chain is `*` types (e.g., multiple AnyType nodes chained), detection returns `*`
- Type detection is JS-only (browser side) — the Python backend doesn't use it
