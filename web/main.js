/**
 * DazzleSwitch - Smart Switch Extension
 *
 * Manages the dynamic dropdown widget that shows connected input names.
 * Handles:
 * - Rebuilding dropdown options on connection changes
 * - Mapping display labels (user-renamed slots) to internal names
 * - Serializing internal names to Python (not display labels)
 * - Workflow save/load with correct dropdown state
 *
 * COMPATIBILITY NOTE:
 * Uses dynamic imports with auto-depth detection to work in both:
 * - Standalone mode: /extensions/ComfyUI-DazzleSwitch/
 * - DazzleNodes mode: /extensions/DazzleNodes/ComfyUI-DazzleSwitch/
 */

// Dynamic import helper for standalone vs nested extension compatibility
async function importComfyCore() {
    const currentPath = import.meta.url;
    const urlParts = new URL(currentPath).pathname.split('/').filter(p => p);
    const depth = urlParts.length;
    const prefix = '../'.repeat(depth);

    const appModule = await import(`${prefix}scripts/app.js`);
    return { app: appModule.app };
}


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
 * Build the list of connected input names and the name map.
 *
 * @param {object} node - ComfyUI node
 * @returns {{labels: string[], nameMap: Object}} Display labels and label→internal name map
 */
function buildConnectedInputInfo(node) {
    const labels = [];
    const nameMap = {};

    if (!node.inputs) {
        return { labels, nameMap };
    }

    for (const input of node.inputs) {
        // Only process our input_XX slots
        if (!input.name || !input.name.startsWith('input_')) {
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
 * Preserves the current selection if it's still valid.
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

    // Preserve selection if still valid
    if (labels.includes(previousValue)) {
        selectWidget.value = previousValue;
    } else {
        // Auto-select first connected input
        selectWidget.value = labels[0];
    }
}


/**
 * Set up the DazzleSwitch node.
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

    // Initialize name map
    node._dsNameMap = {};

    // Override serializeValue to send internal names to Python
    const origSerialize = selectWidget.serializeValue;
    selectWidget.serializeValue = function() {
        const nameMap = node._dsNameMap || {};
        // Convert display label → internal name for Python
        return nameMap[this.value] || this.value;
    };

    // Hook into onConnectionsChange to rebuild dropdown
    const origOnConnectionsChange = node.onConnectionsChange;
    node.onConnectionsChange = function(type, index, connected, link_info, ioSlot) {
        if (origOnConnectionsChange) {
            origOnConnectionsChange.call(this, type, index, connected, link_info, ioSlot);
        }

        // Only rebuild on input connection changes
        // type: 1 = INPUT, 2 = OUTPUT (LiteGraph constants)
        if (type === 1) {
            updateSelectWidget(this);
        }
    };

    // Hook into onConfigure for workflow load
    const origOnConfigure = node.onConfigure;
    node.onConfigure = function(info) {
        if (origOnConfigure) {
            origOnConfigure.call(this, info);
        }

        // Delay rebuild to allow connections to be established first
        setTimeout(() => {
            updateSelectWidget(this);
        }, 100);
    };

    // Initial dropdown build (delayed to allow connections to be established)
    setTimeout(() => {
        updateSelectWidget(node);
    }, 100);
}


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

    console.log("[DazzleSwitch] JavaScript extension loaded");
})();
