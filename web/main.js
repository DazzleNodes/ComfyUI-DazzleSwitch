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
 * - Slot reordering via right-click Move Up / Move Down (swap-and-rename)
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
const NONE_SELECTION = '(none)';
const NO_CONNECTIONS = '(none connected)';

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
 * - "(none)" is always the first option when inputs are connected
 *   (user selects this to skip dropdown and let mode decide)
 * - If the current selection is still connected: keep it
 * - If the current selection was disconnected but others remain: keep it
 *   (user is likely re-wiring; Python falls back per mode at execution)
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
        selectWidget.options.values = [NO_CONNECTIONS];
        selectWidget.value = NO_CONNECTIONS;
        return;
    }

    const previousValue = selectWidget.value;
    // Always include (none) as the first option — lets user opt out of dropdown
    selectWidget.options.values = [NONE_SELECTION, ...labels];

    if (previousValue === NONE_SELECTION) {
        // User explicitly chose (none) — keep it
        selectWidget.value = NONE_SELECTION;
    } else if (labels.includes(previousValue)) {
        // Current selection is still connected — keep it
        selectWidget.value = previousValue;
    } else if (previousValue === NO_CONNECTIONS) {
        // First connection — auto-select it
        selectWidget.value = labels[0];
    }
    // Otherwise: user's selected input was disconnected but others remain.
    // Keep the widget value as-is (preserves user intent during re-wiring).
    // Python switch() will fall back per mode at execution time.
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

/** Opacity multiplier for dimming select_override widget when value is 0. */
const DISABLED_WIDGET_ALPHA = 0.35;

/**
 * Find the slot index of the currently selected input.
 *
 * @param {object} node - ComfyUI node
 * @returns {number} Slot index in node.inputs, or -1 if not found
 */
function getSelectedSlotIndex(node) {
    const selectWidget = node.widgets?.find(w => w.name === 'select');
    if (!selectWidget || selectWidget.value === NO_CONNECTIONS || selectWidget.value === NONE_SELECTION) return -1;

    const nameMap = node._dsNameMap || {};
    const internalName = nameMap[selectWidget.value] || selectWidget.value;

    if (!node.inputs) return -1;
    for (let i = 0; i < node.inputs.length; i++) {
        if (node.inputs[i].name === internalName) return i;
    }
    return -1;
}

/**
 * Dim select_override widget when its value is 0 (override inactive).
 *
 * Provides a custom draw method that renders the widget identically to
 * ComfyUI's built-in number widget (capsule background, arrow buttons,
 * label + value text) but with reduced alpha when value is 0.
 *
 * Unlike using widget.disabled (which hides arrows and outline entirely),
 * this renders everything — just dimmer — so the user can see it's a
 * real widget they can interact with.
 *
 * Rendering matches ComfyUI frontend's BaseSteppedWidget:
 * - drawWidgetShape: capsule background with rounded corners
 * - drawArrowButtons: left/right triangles for increment/decrement
 * - drawTruncatingText: label (left) + value (right)
 *
 * @param {object} node - ComfyUI node
 */
function installOverrideDim(node) {
    const overrideWidget = node.widgets?.find(w => w.name === 'select_override');
    if (!overrideWidget) return;

    // Only install once
    if (overrideWidget._dsDimInstalled) return;
    overrideWidget._dsDimInstalled = true;

    // Constants matching ComfyUI's BaseWidget layout
    const MARGIN = 15;
    const ARROW_MARGIN = 6;
    const ARROW_WIDTH = 6;

    overrideWidget.draw = function(ctx, nodeRef, width, y, height, lowQuality) {
        const dim = (this.value === 0);
        const showText = !lowQuality;
        const savedAlpha = ctx.globalAlpha;

        if (dim) ctx.globalAlpha *= DISABLED_WIDGET_ALPHA;

        // ── Capsule background (BaseWidget.drawWidgetShape) ──
        const outlineColor = this.outline_color
            || LiteGraph.WIDGET_OUTLINE_COLOR || "#666";
        ctx.fillStyle = this.background_color || "#222";
        ctx.beginPath();
        if (showText) {
            ctx.roundRect(MARGIN, y, width - MARGIN * 2, height, [height * 0.5]);
        } else {
            ctx.rect(MARGIN, y, width - MARGIN * 2, height);
        }
        ctx.fill();
        if (showText) {
            ctx.strokeStyle = outlineColor;
            ctx.stroke();
        }

        if (showText) {
            const textColor = this.text_color || "#DDD";
            const dimTextColor = this.disabledTextColor || "#555";

            // ── Arrow buttons (BaseSteppedWidget.drawArrowButtons) ──
            const tipX = MARGIN + ARROW_MARGIN;
            const innerX = tipX + ARROW_WIDTH;
            const minVal = this.options?.min ?? -Infinity;
            const maxVal = this.options?.max ?? Infinity;

            // Left arrow
            ctx.fillStyle = (this.value > minVal) ? textColor : dimTextColor;
            ctx.beginPath();
            ctx.moveTo(innerX, y + 5);
            ctx.lineTo(tipX, y + height * 0.5);
            ctx.lineTo(innerX, y + height - 5);
            ctx.fill();

            // Right arrow
            ctx.fillStyle = (this.value < maxVal) ? textColor : dimTextColor;
            ctx.beginPath();
            ctx.moveTo(width - innerX, y + 5);
            ctx.lineTo(width - tipX, y + height * 0.5);
            ctx.lineTo(width - innerX, y + height - 5);
            ctx.fill();

            // ── Label + Value text ──
            const labelX = MARGIN * 2 + 5;
            const valueX = width - MARGIN * 2 - 10;

            // Label (left-aligned, secondary color)
            ctx.fillStyle = this.secondary_text_color || "#AAA";
            ctx.textAlign = "left";
            ctx.fillText(this.label || this.name, labelX, y + height * 0.7);

            // Value (right-aligned, primary color)
            ctx.fillStyle = textColor;
            ctx.textAlign = "right";
            ctx.fillText(String(this.value), valueX, y + height * 0.7);
        }

        ctx.globalAlpha = savedAlpha;
    };
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

// ─── Slot Reordering ─────────────────────────────────────────────────────────

/**
 * Get the array indices of all input_XX slots in node.inputs[].
 * Excludes select_override and any other non-input slots.
 *
 * @param {object} node - ComfyUI node
 * @returns {number[]} Array of indices into node.inputs[]
 */
function getInputXXIndices(node) {
    const indices = [];
    if (!node.inputs) return indices;
    for (let i = 0; i < node.inputs.length; i++) {
        if (node.inputs[i].name && INPUT_SLOT_RE.test(node.inputs[i].name)) {
            indices.push(i);
        }
    }
    return indices;
}


/**
 * Move an input slot from one position to another in node.inputs[].
 *
 * Uses the swap-and-rename approach:
 * 1. Splice the array (move, not swap)
 * 2. Rename all input_XX slots sequentially by new position
 * 3. Re-key the label cache to match new names
 * 4. Patch graph.links[].target_slot for all connected inputs
 * 5. Re-trigger stabilize (rebuilds dropdown, type detection, etc.)
 *
 * @param {object} node - ComfyUI node
 * @param {number} fromIndex - Current index in node.inputs[]
 * @param {number} toIndex - Target index in node.inputs[]
 */
function moveInputSlot(node, fromIndex, toIndex) {
    if (fromIndex === toIndex) return;
    if (!node.inputs || !node.graph) return;

    // 1. Cancel any pending stabilize (prevent it from undoing our reorder)
    const existing = _stabilizeTimers.get(node);
    if (existing) {
        clearTimeout(existing);
        _stabilizeTimers.delete(node);
    }

    // 2. Splice the inputs array (move the slot object to new position)
    const inputs = node.inputs;
    inputs.splice(toIndex, 0, inputs.splice(fromIndex, 1)[0]);

    // 3. Rename all input_XX slots sequentially by their new position
    let inputNum = 1;
    const nameRemap = {};  // oldName → newName
    for (let i = 0; i < inputs.length; i++) {
        if (!INPUT_SLOT_RE.test(inputs[i].name)) continue;

        const oldName = inputs[i].name;
        const newName = `input_${String(inputNum).padStart(2, '0')}`;
        if (oldName !== newName) {
            nameRemap[oldName] = newName;
            inputs[i].name = newName;
        }
        inputNum++;
    }

    // 4. Re-key label cache to match renamed slots
    if (node._dsLabelCache && Object.keys(nameRemap).length > 0) {
        const newCache = {};
        for (const [key, label] of Object.entries(node._dsLabelCache)) {
            newCache[nameRemap[key] || key] = label;
        }
        node._dsLabelCache = newCache;
    }

    // 5. Patch link target_slot indices for ALL inputs
    //    (rgthree-proven pattern: walk inputs, set target_slot = current index)
    for (let i = 0; i < inputs.length; i++) {
        if (inputs[i].link != null) {
            const link = node.graph.links[inputs[i].link];
            if (link) {
                link.target_slot = i;
            }
        }
    }

    // 6. Stabilize: rebuilds dropdown, type detection, label watchers
    stabilize(node);
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
        // Special values pass through as-is
        if (this.value === NONE_SELECTION || this.value === NO_CONNECTIONS) {
            return this.value;
        }
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

    // Dim select_override widget when value is 0 (visually indicates "disabled")
    installOverrideDim(node);

    // Hook into onDrawForeground for active slot highlight
    const origOnDrawForeground = node.onDrawForeground;
    node.onDrawForeground = function(ctx, canvas) {
        if (origOnDrawForeground) {
            origOnDrawForeground.call(this, ctx, canvas);
        }
        drawActiveSlotHighlight(this, ctx, canvas);
    };

    // Slot reordering context menu (Move Up / Move Down)
    const origGetSlotMenuOptions = node.getSlotMenuOptions;
    node.getSlotMenuOptions = function(slot) {
        const options = origGetSlotMenuOptions?.call(this, slot) || [];

        // Only add reorder options for input_XX slots
        if (slot.input && INPUT_SLOT_RE.test(slot.input.name)) {
            const currentIndex = slot.slot;
            const inputIndices = getInputXXIndices(this);
            const posInRange = inputIndices.indexOf(currentIndex);

            if (posInRange >= 0) {
                if (options.length > 0) options.push(null);  // separator

                options.push({
                    content: "\u2B06\uFE0F Move Up",
                    disabled: posInRange <= 0,
                    callback: () => {
                        moveInputSlot(this, currentIndex, inputIndices[posInRange - 1]);
                    }
                });
                options.push({
                    content: "\u2B07\uFE0F Move Down",
                    disabled: posInRange >= inputIndices.length - 1,
                    callback: () => {
                        moveInputSlot(this, currentIndex, inputIndices[posInRange + 1]);
                    }
                });
            }
        }

        return options;
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

    console.log("[DazzleSwitch] JavaScript extension loaded (Phase 4: fallback modes)");
})();
