/**
 * Configuration API Client
 * Provides methods to interact with deployment configuration endpoints
 */

const ConfigClient = {
    /**
     * Get current deployment mode configuration
     * @returns {Promise<Object>} Configuration object with mode, configured_at, updated_at
     */
    async getDeploymentMode() {
        try {
            const response = await fetch('/api/config/deployment-mode');

            if (!response.ok) {
                throw new Error(`Failed to get deployment mode: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('ConfigClient.getDeploymentMode error:', error);
            throw error;
        }
    },

    /**
     * Set deployment mode (requires admin authentication)
     * @param {string} mode - "single-user" or "multi-user"
     * @returns {Promise<Object>} Updated configuration object
     */
    async setDeploymentMode(mode) {
        try {
            if (!mode || !['single-user', 'multi-user'].includes(mode)) {
                throw new Error('Invalid mode. Must be "single-user" or "multi-user"');
            }

            const response = await fetch('/api/config/deployment-mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mode })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Failed to set deployment mode');
            }

            return await response.json();
        } catch (error) {
            console.error('ConfigClient.setDeploymentMode error:', error);
            throw error;
        }
    },

    /**
     * Validate deployment mode consistency between environment and database
     * @returns {Promise<Object>} Validation result with valid flag, env_mode, db_mode, message
     */
    async validateModeConsistency() {
        try {
            const response = await fetch('/api/config/deployment-mode/validate');

            if (!response.ok) {
                throw new Error(`Failed to validate mode consistency: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('ConfigClient.validateModeConsistency error:', error);
            throw error;
        }
    },

    /**
     * Check system health and get current deployment mode
     * @returns {Promise<Object>} Health check result with status, deployment_mode, timestamp
     */
    async healthCheck() {
        try {
            const response = await fetch('/api/config/health');

            if (!response.ok) {
                throw new Error(`Health check failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('ConfigClient.healthCheck error:', error);
            throw error;
        }
    },

    /**
     * Check if system is in single-user mode
     * @returns {Promise<boolean>} True if in single-user mode
     */
    async isSingleUserMode() {
        try {
            const config = await this.getDeploymentMode();
            return config.mode === 'single-user';
        } catch (error) {
            console.error('ConfigClient.isSingleUserMode error:', error);
            // Default to single-user mode if check fails
            return true;
        }
    },

    /**
     * Check if system is in multi-user mode
     * @returns {Promise<boolean>} True if in multi-user mode
     */
    async isMultiUserMode() {
        try {
            const config = await this.getDeploymentMode();
            return config.mode === 'multi-user';
        } catch (error) {
            console.error('ConfigClient.isMultiUserMode error:', error);
            // Default to single-user mode if check fails
            return false;
        }
    },

    /**
     * Format configuration object for display
     * @param {Object} config - Configuration object
     * @returns {Object} Formatted configuration with readable strings
     */
    formatConfig(config) {
        if (!config) {
            return {
                mode: 'Unknown',
                modeDescription: 'Unable to determine deployment mode',
                configuredAt: 'Unknown',
                updatedAt: 'Unknown'
            };
        }

        const modeDescriptions = {
            'single-user': 'Single-User Mode (No authentication)',
            'multi-user': 'Multi-User Mode (With authentication)'
        };

        return {
            mode: config.mode || 'Unknown',
            modeDescription: modeDescriptions[config.mode] || 'Unknown mode',
            configuredAt: config.configured_at ? new Date(config.configured_at).toLocaleString() : 'Unknown',
            updatedAt: config.updated_at ? new Date(config.updated_at).toLocaleString() : 'Unknown'
        };
    }
};

// Export for use in modules (if supported)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConfigClient;
}
