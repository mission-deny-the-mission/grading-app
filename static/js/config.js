/**
 * Configuration page JavaScript functionality
 * Handles API key validation, testing, and bulk operations
 */

// API Key regex patterns (must match server-side patterns in utils/llm_providers.py)
const API_KEY_PATTERNS = {
    openrouter: /^sk-or-v1-[a-zA-Z0-9]{64}$/,
    claude: /^sk-ant-api03-[A-Za-z0-9_-]{95}$/,
    gemini: /^AIza[0-9A-Za-z_-]{35}$/,
    openai: /^sk-[a-zA-Z0-9]{48}$/,
    nanogpt: /^[a-zA-Z0-9_-]{32,}$/,
    chutes: /^chutes_[a-zA-Z0-9_]{32,}$/,
    zai: /^[a-zA-Z0-9_-]{32,}$/,
};

/**
 * Validate API key format on client side (T065, T066)
 * @param {string} provider - Provider name (e.g., 'openrouter')
 * @param {string} key - API key to validate
 * @returns {boolean} - True if format is valid
 */
function validateKeyFormat(provider, key) {
    if (!key || key.trim() === '') {
        return true; // Empty keys are allowed
    }

    const pattern = API_KEY_PATTERNS[provider];
    if (!pattern) {
        return false; // Unknown provider
    }

    return pattern.test(key);
}

/**
 * Test an API key by calling the /test_api_key endpoint (T066)
 * @param {string} provider - Provider name
 * @param {string} key - API key to test
 */
async function testApiKey(provider, key) {
    if (!key || key.trim() === '') {
        showMessage(`No ${provider} API key provided`, 'error');
        return;
    }

    if (!validateKeyFormat(provider, key)) {
        showMessage(`Invalid ${provider} API key format`, 'error');
        return;
    }

    try {
        const response = await fetch('/test_api_key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: provider,
                key: key
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(`✓ ${provider} API key is valid`, 'success');
        } else {
            showMessage(`✗ ${provider} API error: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showMessage(`Failed to test ${provider} API key: ${error.message}`, 'error');
    }
}

/**
 * Export configuration to JSON file (T065)
 */
async function exportConfig() {
    try {
        // T067: Show security warning
        const confirmed = confirm(
            'WARNING: The exported file will contain sensitive API keys.\n\n' +
            'Please protect this file carefully. Do not commit it to version control.\n\n' +
            'Do you want to continue?'
        );

        if (!confirmed) {
            return;
        }

        const response = await fetch('/export_config');
        if (!response.ok) {
            const errorData = await response.json();
            showMessage(`Failed to export configuration: ${errorData.error}`, 'error');
            return;
        }

        const configData = await response.json();

        // Create a blob from the JSON data
        const blob = new Blob(
            [JSON.stringify(configData, null, 2)],
            { type: 'application/json' }
        );

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `config-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(link);

        showMessage('✓ Configuration exported successfully', 'success');
    } catch (error) {
        showMessage(`Failed to export configuration: ${error.message}`, 'error');
    }
}

/**
 * Import configuration from JSON file (T066)
 * @param {File} file - File to import
 */
async function importConfig(file) {
    if (!file) {
        return;
    }

    try {
        // Read file contents
        const fileContent = await file.text();
        const configData = JSON.parse(fileContent);

        // Send to server
        const response = await fetch('/import_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(configData)
        });

        const data = await response.json();

        if (data.success) {
            showMessage(
                `✓ Configuration imported successfully (${data.fields_updated} fields updated)`,
                'success'
            );
            // Reload the page to reflect changes
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            // Show validation errors if available
            let errorMsg = data.error;
            if (data.validation_errors && data.validation_errors.length > 0) {
                errorMsg += '\n\nValidation errors:\n' + data.validation_errors.join('\n');
            }
            showMessage(`✗ Failed to import: ${errorMsg}`, 'error');
        }
    } catch (error) {
        showMessage(
            `Failed to import configuration: ${error.message}`,
            'error'
        );
    }
}

/**
 * Display a message to the user (T070)
 * @param {string} message - Message to display
 * @param {string} type - Message type ('success' or 'error')
 */
function showMessage(message, type) {
    // Create message element if it doesn't exist
    let messageContainer = document.getElementById('import-export-messages');
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'import-export-messages';
        const configForm = document.querySelector('form') || document.body;
        configForm.insertBefore(messageContainer, configForm.firstChild);
    }

    // Create message element
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    messageElement.setAttribute('role', 'alert');
    messageElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    messageContainer.appendChild(messageElement);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}

// Set up event handlers when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Set up export button
    const exportButton = document.getElementById('export-config-btn');
    if (exportButton) {
        exportButton.addEventListener('click', exportConfig);
    }

    // Set up import file input
    const importFileInput = document.getElementById('import-config-file');
    if (importFileInput) {
        importFileInput.addEventListener('change', function(e) {
            if (this.files.length > 0) {
                importConfig(this.files[0]);
                // Reset the input for future imports
                this.value = '';
            }
        });
    }

    // Set up test buttons for each provider
    const testButtonsConfig = {
        'openrouter-test-btn': 'openrouter',
        'claude-test-btn': 'claude',
        'gemini-test-btn': 'gemini',
        'openai-test-btn': 'openai',
        'nanogpt-test-btn': 'nanogpt',
        'chutes-test-btn': 'chutes',
        'zai-test-btn': 'zai',
    };

    Object.entries(testButtonsConfig).forEach(([buttonId, provider]) => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', function() {
                const keyInputId = `${provider}-api-key-input`;
                const keyInput = document.getElementById(keyInputId);
                if (keyInput) {
                    testApiKey(provider, keyInput.value);
                }
            });
        }
    });
});
