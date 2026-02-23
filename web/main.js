/**
 * DazzleSwitch - Smart Switch Extension
 *
 * Manages dynamic input slots, dropdown widget, and type detection.
 * Handles:
 * - Dynamic input expansion (grow on connect, shrink on disconnect, min 3)
 * - Rebuilding dropdown options on connection changes
 * - Mapping display labels (user-renamed slots) to internal names
 * - Type detection via connection graph walking
 * - Output type label showing detected type of selected input
 * - Serializing internal names to Python (not display labels)
 * - Workflow save/load with correct state
 *
 * COMPATIBILITY NOTE:
 * Uses dynamic imports with auto-depth detection to work in both:
 * - Standalone mode: /extensions/ComfyUI-DazzleSwitch/
 * - DazzleNodes mode: /extensions/DazzleNodes/ComfyUI-DazzleSwitch/
 */

// ─── Constants ───────────────────────────────────────────────────────────────

const MIN_INPUT_SLOTS = 3;
const STABILIZE_DEBOUNCE_MS = 64;
const TYPE_WALK_MAX_DEPTH = 10;
const INPUT_SLOT_RE = /^input_(\d{2})$/;

// ─── Dynamic Import ──────────────────────────────────────────────────────────

// Dynamic import helper for standalone vs nested extension compatibility
async function importComfyCore() {
    const currentPath = import.meta.url;
    const urlParts = new URL(currentPath).pathname.split('/').filter(p => p);
    const depth = urlParts.length;
    const prefix = '../'.repeat(depth);

    const appModule = await import(`${prefix}scripts/app.js`);
    return { app: appModule.app };
}

// ─── Debounce ────────────────────────────────────────────────────────────────

// Per-node debounce timers (WeakMap so GC cleans up removed nodes)
const _stabilizeTimers = new WeakMap();

/**
 * Schedule a debounced stabilize for a node.
 * Collapses rapid connection changes into a single stabilize call.
 *
 * @param {object} node - ComfyUI node
 */
function scheduleStabilize(node) {
    const existing = _stabilizeTimers.get(node);
    if (existing) {
        clearTimeout(existing);
    }
    const timer = setTimeout(() => {
        _stabilizeTimers.delete(node);
        stabilize(node);
    }, STABILIZE_DEBOUNCE_MS);
    _stabilizeTimers.set(node, timer);
}

// ─── Slot Management ─────────────────────────────────────────────────────────

/**
 * Get display label for an input slot.
 * Uses user-renamed label if available, otherwise the internal name.
 *
 * @param {object} input - LiteGraph input slot object
 * @returns {string} Display label
 */
function getInputLabel(input) {
    return input.label || input.name;
}


/**
 * Count how many input_XX slots the node currently has.
 *
 * @param {object} node - ComfyUI node
 * @returns {number} Count of input_XX slots
 */
function countInputSlots(node) {
    if (!node.inputs) return 0;
    let count = 0;
    for (const input of node.inputs) {
        if (input.name && INPUT_SLOT_RE.test(input.name)) {
            count++;
        }
    }
    return count;
}


/**
 * Find the highest input_XX number among current slots.
 *
 * @param {object} node - ComfyUI node
 * @returns {number} Highest input number (0 if none)
 */
function getHighestInputNumber(node) {
    let highest = 0;
    if (!node.inputs) return highest;
    for (const input of node.inputs) {
        const m = input.name?.match(INPUT_SLOT_RE);
        if (m) {
            highest = Math.max(highest, parseInt(m[1], 10));
        }
    }
    return highest;
}


/**
 * Remove unconnected input_XX slots from the end, keeping at least MIN_INPUT_SLOTS.
 * Iterates backward so slot indices stay stable during removal.
 *
 * @param {object} node - ComfyUI node
 */
function removeUnusedInputsFromEnd(node) {
    if (!node.inputs) return;

    // Walk backward through inputs
    for (let i = node.inputs.length - 1; i >= 0; i--) {
        const input = node.inputs[i];
        if (!input.name || !INPUT_SLOT_RE.test(input.name)) {
            continue;
        }

        // Stop removing if we'd go below minimum
        if (countInputSlots(node) <= MIN_INPUT_SLOTS) {
            break;
        }

        // Stop at the first connected slot — don't remove past it
        if (input.link != null) {
            break;
        }

        // Cache label before removal so it can be restored on reconnect
        if (input.label && node._dsLabelCache) {
            node._dsLabelCache[input.name] = input.label;
        }

        node.removeInput(i);
    }
}


/**
 * Add a buffer input slot if the last input_XX slot is connected.
 * Ensures there's always one empty slot for the user to connect to.
 *
 * @param {object} node - ComfyUI node
 */
function addBufferInputIfNeeded(node) {
    if (!node.inputs) return;

    // Find the last input_XX slot
    let lastInputSlot = null;
    for (let i = node.inputs.length - 1; i >= 0; i--) {
        if (node.inputs[i].name && INPUT_SLOT_RE.test(node.inputs[i].name)) {
            lastInputSlot = node.inputs[i];
            break;
        }
    }

    // If last slot is connected, add a new one
    if (lastInputSlot && lastInputSlot.link != null) {
        const nextNum = getHighestInputNumber(node) + 1;
        const name = `input_${String(nextNum).padStart(2, '0')}`;
        node.addInput(name, "*");

        // Restore cached label if this slot was previously named
        if (node._dsLabelCache && node._dsLabelCache[name]) {
            const newInput = node.inputs[node.inputs.length - 1];
            newInput.label = node._dsLabelCache[name];
        }
    }
}

// ─── Label Watching ──────────────────────────────────────────────────────────

/**
 * Install a property watcher on an input slot's `label` property.
 * When the label changes (e.g., via right-click Rename), schedules a stabilize.
 * Non-invasive: doesn't touch context menus or LiteGraph internals.
 *
 * @param {object} node - ComfyUI node (for stabilize callback)
 * @param {object} input - LiteGraph input slot object
 */
function installLabelWatcher(node, input) {
    if (input._dsLabelWatched) return;

    let _label = input.label;
    Object.defineProperty(input, 'label', {
        get() { return _label; },
        set(val) {
            if (_label !== val) {
                _label = val;
                scheduleStabilize(node);
            } else {
                _label = val;
            }
        },
        configurable: true,
        enumerable: true,
    });
    input._dsLabelWatched = true;
}


/**
 * Ensure all input_XX slots on a node have label watchers installed.
 * Called during stabilize so dynamically-added slots get watched too.
 *
 * @param {object} node - ComfyUI node
 */
function watchInputLabels(node) {
    if (!node.inputs) return;
    for (const input of node.inputs) {
        if (input.name && INPUT_SLOT_RE.test(input.name)) {
            installLabelWatcher(node, input);
        }
    }
}

// ─── Type Detection ──────────────────────────────────────────────────────────

/**
 * Follow a connection chain backward to find the first non-"*" type.
 * Handles Reroute nodes and chained DazzleSwitches (both output "*").
 *
 * @param {object} graph - LiteGraph graph instance
 * @param {object} node - Starting node
 * @param {number} slotIndex - Input slot index on the starting node
 * @param {Set} visited - Set of visited link IDs (prevents infinite loops)
 * @param {number} depth - Current recursion depth
 * @returns {string} Detected type, or "*" if chain is all wildcards
 */
function followConnectionUntilType(graph, node, slotIndex, visited, depth) {
    if (depth >= TYPE_WALK_MAX_DEPTH) return "*";
    if (!node.inputs || slotIndex < 0 || slotIndex >= node.inputs.length) return "*";

    const input = node.inputs[slotIndex];
    if (input.link == null) return "*";

    // Prevent infinite loops
    if (visited.has(input.link)) return "*";
    visited.add(input.link);

    const linkInfo = graph.links[input.link];
    if (!linkInfo) return "*";

    const sourceNode = graph.getNodeById(linkInfo.origin_id);
    if (!sourceNode) return "*";

    const sourceSlotIndex = linkInfo.origin_slot;
    if (!sourceNode.outputs || sourceSlotIndex >= sourceNode.outputs.length) return "*";

    const sourceOutput = sourceNode.outputs[sourceSlotIndex];
    const sourceType = sourceOutput.type;

    // Found a real type
    if (sourceType && sourceType !== "*") {
        return sourceType;
    }

    // Source is also "*" — recurse into its inputs
    // Try to find the corresponding input on the source node
    // For Reroute: single input at index 0
    // For DazzleSwitch or similar: try first connected input
    if (sourceNode.inputs) {
        for (let i = 0; i < sourceNode.inputs.length; i++) {
            if (sourceNode.inputs[i].link != null) {
                const result = followConnectionUntilType(graph, sourceNode, i, visited, depth + 1);
                if (result !== "*") return result;
            }
        }
    }

    return "*";
}


/**
 * Detect the type of the currently selected input.
 *
 * @param {object} node - ComfyUI node
 * @returns {string} Detected type, or "*"
 */
function getSelectedInputType(node) {
    const graph = node.graph;
    if (!graph || !node.inputs) return "*";

    // Find which input is currently selected
    const selectWidget = node.widgets?.find(w => w.name === 'select');
    if (!selectWidget) return "*";

    const nameMap = node._dsNameMap || {};
    const internalName = nameMap[selectWidget.value] || selectWidget.value;

    // Find the slot index for this internal name
    for (let i = 0; i < node.inputs.length; i++) {
        if (node.inputs[i].name === internalName) {
            return followConnectionUntilType(graph, node, i, new Set(), 0);
        }
    }

    return "*";
}


/**
 * Update the output slot's type and label to match the detected type.
 *
 * @param {object} node - ComfyUI node
 * @param {string} type - Detected type string
 */
function updateOutputType(node, type) {
    if (!node.outputs || node.outputs.length === 0) return;

    const output = node.outputs[0];
    const newType = type || "*";

    if (output.type !== newType) {
        output.type = newType;
        output.label = newType === "*" ? "output" : newType;
    }
}

// ─── Dropdown Widget ─────────────────────────────────────────────────────────

/**
 * Build the list of connected input names and the name map.
 *
 * @param {object} node - ComfyUI node
 * @returns {{labels: string[], nameMap: Object}} Display labels and label-to-internal name map
 */
function buildConnectedInputInfo(node) {
    const labels = [];
    const nameMap = {};

    if (!node.inputs) {
        return { labels, nameMap };
    }

    for (const input of node.inputs) {
        // Only process our input_XX slots
        if (!input.name || !INPUT_SLOT_RE.test(input.name)) {
            continue;
        }

        // Only include connected inputs
        if (input.link == null) {
            continue;
        }

        const displayLabel = getInputLabel(input);
        labels.push(displayLabel);
        nameMap[displayLabel] = input.name;
    }

    return { labels, nameMap };
}


/**
 * Update the select dropdown widget with current connected input names.
 *
 * Selection preservation strategy:
 * - If the current selection is still connected: keep it
 * - If the current selection was disconnected but others remain: keep it
 *   (user is likely re-wiring; Python falls back to first connected at execution)
 * - If nothing is connected: show "(none connected)"
 * - Only auto-select on first connection (from "(none connected)" state)
 *
 * @param {object} node - ComfyUI node
 */
function updateSelectWidget(node) {
    const selectWidget = node.widgets?.find(w => w.name === 'select');
    if (!selectWidget) {
        return;
    }

    const { labels, nameMap } = buildConnectedInputInfo(node);
    node._dsNameMap = nameMap;

    if (labels.length === 0) {
        selectWidget.options.values = ['(none connected)'];
        selectWidget.value = '(none connected)';
        return;
    }

    const previousValue = selectWidget.value;
    selectWidget.options.values = labels;

    if (labels.includes(previousValue)) {
        // Current selection is still connected — keep it
        selectWidget.value = previousValue;
    } else if (previousValue === '(none connected)') {
        // First connection — auto-select it
        selectWidget.value = labels[0];
    }
    // Otherwise: user's selected input was disconnected but others remain.
    // Keep the widget value as-is (preserves user intent during re-wiring).
    // Python switch() will fall back to first connected at execution time.
}

// ─── Stabilize Cycle ─────────────────────────────────────────────────────────

/**
 * Main stabilize function — orchestrates slot management, dropdown update,
 * and type detection in a single debounced cycle.
 *
 * Order matters:
 * 1. Remove unused trailing slots (shrink)
 * 2. Add buffer slot if last is connected (grow)
 * 3. Rebuild dropdown from current connections
 * 4. Detect type of selected input and update output label
 *
 * @param {object} node - ComfyUI node
 */
function stabilize(node) {
    // 1. Shrink: remove unused trailing input slots
    removeUnusedInputsFromEnd(node);

    // 2. Grow: add buffer if last slot is connected
    addBufferInputIfNeeded(node);

    // 3. Install label watchers on any new slots (from grow step)
    watchInputLabels(node);

    // 4. Rebuild dropdown
    updateSelectWidget(node);

    // 5. Type detection and output label
    const detectedType = getSelectedInputType(node);
    updateOutputType(node, detectedType);

    // Trigger visual refresh
    node.setDirtyCanvas(true, true);
}

// ─── Active Slot Highlight ───────────────────────────────────────────────────

/** Semi-transparent background tint for the active (selected) input slot. */
const ACTIVE_SLOT_TINT = "rgba(91, 189, 91, 0.15)";

/**
 * Find the slot index of the currently selected input.
 *
 * @param {object} node - ComfyUI node
 * @returns {number} Slot index in node.inputs, or -1 if not found
 */
function getSelectedSlotIndex(node) {
    const selectWidget = node.widgets?.find(w => w.name === 'select');
    if (!selectWidget || selectWidget.value === '(none connected)') return -1;

    const nameMap = node._dsNameMap || {};
    const internalName = nameMap[selectWidget.value] || selectWidget.value;

    if (!node.inputs) return -1;
    for (let i = 0; i < node.inputs.length; i++) {
        if (node.inputs[i].name === internalName) return i;
    }
    return -1;
}

/**
 * Draw a subtle border highlight on the selected input slot.
 * Called from onDrawForeground — coordinates are node-relative.
 * Uses LiteGraph's getConnectionPos() for accurate slot positioning.
 *
 * @param {object} node - ComfyUI node
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {object} canvas - LiteGraph canvas
 */
function drawActiveSlotHighlight(node, ctx, canvas) {
    // Skip when collapsed or zoomed out too far
    if (node.flags?.collapsed) return;
    if (canvas?.ds?.scale < 0.5) return;

    const slotIndex = getSelectedSlotIndex(node);
    if (slotIndex < 0) return;

    // Use LiteGraph's own slot positioning (returns absolute coords)
    const pos = new Float32Array(2);
    node.getConnectionPos(true, slotIndex, pos);

    // Convert absolute → node-relative for onDrawForeground context
    const slotCenterY = pos[1] - node.pos[1];
    const slotHeight = LiteGraph.NODE_SLOT_HEIGHT || 20;

    ctx.save();
    ctx.fillStyle = ACTIVE_SLOT_TINT;
    ctx.beginPath();
    ctx.roundRect(0, slotCenterY - slotHeight * 0.5, node.size[0], slotHeight, 3);
    ctx.fill();
    ctx.restore();
}

// ─── Node Setup ──────────────────────────────────────────────────────────────

/**
 * Set up the DazzleSwitch node with all Phase 2 behaviors.
 *
 * @param {object} node - ComfyUI node
 * @param {object} app - ComfyUI app instance
 */
function setupDazzleSwitchNode(node, app) {
    if (!node.widgets) {
        return;
    }

    const selectWidget = node.widgets.find(w => w.name === 'select');
    if (!selectWidget) {
        return;
    }

    // Initialize name map and label cache
    node._dsNameMap = {};
    node._dsLabelCache = {};

    // Override serializeValue to send internal names to Python
    selectWidget.serializeValue = function() {
        const nameMap = node._dsNameMap || {};
        // Convert display label to internal name for Python
        return nameMap[this.value] || this.value;
    };

    // Hook into onConnectionsChange for debounced stabilize
    const origOnConnectionsChange = node.onConnectionsChange;
    node.onConnectionsChange = function(type, index, connected, link_info, ioSlot) {
        if (origOnConnectionsChange) {
            origOnConnectionsChange.call(this, type, index, connected, link_info, ioSlot);
        }

        // Stabilize on input connection changes
        // type: 1 = INPUT, 2 = OUTPUT (LiteGraph constants)
        if (type === 1) {
            scheduleStabilize(this);
        }
    };

    // Hook into onConfigure for workflow load
    const origOnConfigure = node.onConfigure;
    node.onConfigure = function(info) {
        if (origOnConfigure) {
            origOnConfigure.call(this, info);
        }

        // Delay stabilize to allow connections to be established first
        setTimeout(() => {
            stabilize(this);
        }, 100);
    };

    // Listen for dropdown changes to re-detect type
    const origCallback = selectWidget.callback;
    selectWidget.callback = function(value) {
        if (origCallback) {
            origCallback.call(this, value);
        }
        // Re-detect type when user changes dropdown selection
        const detectedType = getSelectedInputType(node);
        updateOutputType(node, detectedType);
        node.setDirtyCanvas(true, true);
    };

    // Hook into onDrawForeground for active slot highlight
    const origOnDrawForeground = node.onDrawForeground;
    node.onDrawForeground = function(ctx, canvas) {
        if (origOnDrawForeground) {
            origOnDrawForeground.call(this, ctx, canvas);
        }
        drawActiveSlotHighlight(this, ctx, canvas);
    };

    // Initial stabilize (delayed to allow connections to be established)
    setTimeout(() => {
        stabilize(node);
    }, 100);
}

// ─── Extension Registration ──────────────────────────────────────────────────

// Initialize extension with dynamic imports
(async () => {
    const { app } = await importComfyCore();

    app.registerExtension({
        name: "DazzleNodes.DazzleSwitch",

        nodeCreated(node, app) {
            if (node.comfyClass !== "DazzleSwitch") {
                return;
            }

            setupDazzleSwitchNode(node, app);
        }
    });

    console.log("[DazzleSwitch] JavaScript extension loaded (Phase 3: label cache + active slot highlight)");
})();
