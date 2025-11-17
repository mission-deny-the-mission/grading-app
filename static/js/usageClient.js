/**
 * Usage Tracking API Client
 * Provides methods to interact with usage tracking and quota management endpoints
 */

const UsageClient = {
    /**
     * Get current user's usage summary
     * @param {Object} params - Query parameters (start_date, end_date, provider)
     * @returns {Promise<Object>} Usage summary with quotas and consumption
     */
    async getUsageSummary(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/usage/summary${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get usage summary');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getUsageSummary error:', error);
            throw error;
        }
    },

    /**
     * Get detailed usage history
     * @param {Object} params - Query parameters (page, per_page, start_date, end_date, provider)
     * @returns {Promise<Object>} Paginated usage history
     */
    async getUsageHistory(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/usage/history${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get usage history');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getUsageHistory error:', error);
            throw error;
        }
    },

    /**
     * Get usage trends (7-day rolling average)
     * @param {string} provider - Optional provider filter
     * @returns {Promise<Object>} Usage trends data
     */
    async getUsageTrends(provider = null) {
        try {
            const params = provider ? { provider } : {};
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/usage/trends${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get usage trends');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getUsageTrends error:', error);
            throw error;
        }
    },

    /**
     * Get current user's quotas
     * @returns {Promise<Object>} User quotas by provider
     */
    async getQuotas() {
        try {
            const response = await fetch('/api/usage/quotas');

            if (!response.ok) {
                throw new Error('Failed to get quotas');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getQuotas error:', error);
            throw error;
        }
    },

    /**
     * Get quotas for a specific user (admin only)
     * @param {number} userId - User ID
     * @returns {Promise<Object>} User quotas
     */
    async getUserQuotas(userId) {
        try {
            const response = await fetch(`/api/usage/quotas/${userId}`);

            if (!response.ok) {
                throw new Error('Failed to get user quotas');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getUserQuotas error:', error);
            throw error;
        }
    },

    /**
     * Update quotas for a specific user (admin only)
     * @param {number} userId - User ID
     * @param {Object} quotas - Quota updates by provider
     * @returns {Promise<Object>} Updated quotas
     */
    async updateUserQuotas(userId, quotas) {
        try {
            const response = await fetch(`/api/usage/quotas/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ quotas })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Quota update failed');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.updateUserQuotas error:', error);
            throw error;
        }
    },

    /**
     * Get system-wide usage analytics (admin only)
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} System usage analytics
     */
    async getSystemAnalytics(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/usage/analytics${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get system analytics');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getSystemAnalytics error:', error);
            throw error;
        }
    },

    /**
     * Get top users by usage (admin only)
     * @param {number} limit - Number of top users to return
     * @param {string} provider - Optional provider filter
     * @returns {Promise<Array>} Top users list
     */
    async getTopUsers(limit = 10, provider = null) {
        try {
            const params = { limit };
            if (provider) params.provider = provider;

            const queryString = new URLSearchParams(params).toString();
            const url = `/api/usage/top-users${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get top users');
            }

            return await response.json();
        } catch (error) {
            console.error('UsageClient.getTopUsers error:', error);
            throw error;
        }
    },

    /**
     * Export usage history to CSV
     * @param {Object} params - Export parameters
     * @returns {Promise<Blob>} CSV file blob
     */
    async exportUsageCSV(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/usage/export${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to export usage data');
            }

            return await response.blob();
        } catch (error) {
            console.error('UsageClient.exportUsageCSV error:', error);
            throw error;
        }
    },

    /**
     * Format usage data for display
     * @param {number} tokens - Token count
     * @returns {string} Formatted token string
     */
    formatTokens(tokens) {
        if (tokens >= 1000000) {
            return `${(tokens / 1000000).toFixed(2)}M`;
        } else if (tokens >= 1000) {
            return `${(tokens / 1000).toFixed(2)}K`;
        }
        return tokens.toString();
    },

    /**
     * Calculate quota percentage
     * @param {number} used - Tokens used
     * @param {number} quota - Total quota
     * @returns {number} Percentage used (0-100)
     */
    calculateQuotaPercentage(used, quota) {
        if (!quota || quota === 0) {
            return 0;
        }
        return Math.min(100, (used / quota) * 100);
    },

    /**
     * Get quota status level
     * @param {number} percentage - Quota percentage used
     * @returns {string} Status level: 'safe', 'warning', 'critical'
     */
    getQuotaStatus(percentage) {
        if (percentage >= 90) {
            return 'critical';
        } else if (percentage >= 75) {
            return 'warning';
        }
        return 'safe';
    },

    /**
     * Get quota status color for Bootstrap
     * @param {number} percentage - Quota percentage used
     * @returns {string} Bootstrap color class
     */
    getQuotaColor(percentage) {
        const status = this.getQuotaStatus(percentage);
        const colors = {
            'safe': 'success',
            'warning': 'warning',
            'critical': 'danger'
        };
        return colors[status];
    }
};

// Export for use in modules (if supported)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UsageClient;
}
