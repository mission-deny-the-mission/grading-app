/**
 * Project Sharing API Client
 * Provides methods to interact with project sharing endpoints
 */

const SharingClient = {
    /**
     * Get projects shared with current user
     * @param {Object} params - Query parameters (page, per_page)
     * @returns {Promise<Object>} Paginated shared projects
     */
    async getSharedProjects(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/sharing/shared-with-me${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get shared projects');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.getSharedProjects error:', error);
            throw error;
        }
    },

    /**
     * Get shares for a specific project
     * @param {number} projectId - Project ID
     * @returns {Promise<Array>} List of project shares
     */
    async getProjectShares(projectId) {
        try {
            const response = await fetch(`/api/sharing/projects/${projectId}/shares`);

            if (!response.ok) {
                throw new Error('Failed to get project shares');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.getProjectShares error:', error);
            throw error;
        }
    },

    /**
     * Share a project with a user
     * @param {number} projectId - Project ID
     * @param {number} userId - User ID to share with
     * @param {string} permission - Permission level ('read' or 'write')
     * @returns {Promise<Object>} Created share
     */
    async shareProject(projectId, userId, permission = 'read') {
        try {
            const response = await fetch(`/api/sharing/projects/${projectId}/share`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    permission
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Sharing failed');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.shareProject error:', error);
            throw error;
        }
    },

    /**
     * Update share permission
     * @param {number} shareId - Share ID
     * @param {string} permission - New permission level
     * @returns {Promise<Object>} Updated share
     */
    async updateSharePermission(shareId, permission) {
        try {
            const response = await fetch(`/api/sharing/shares/${shareId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ permission })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Permission update failed');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.updateSharePermission error:', error);
            throw error;
        }
    },

    /**
     * Revoke project share
     * @param {number} shareId - Share ID
     * @returns {Promise<Object>} Revocation response
     */
    async revokeShare(shareId) {
        try {
            const response = await fetch(`/api/sharing/shares/${shareId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Revocation failed');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.revokeShare error:', error);
            throw error;
        }
    },

    /**
     * Check user's permission for a project
     * @param {number} projectId - Project ID
     * @returns {Promise<Object>} Permission check result
     */
    async checkProjectPermission(projectId) {
        try {
            const response = await fetch(`/api/sharing/projects/${projectId}/permission`);

            if (!response.ok) {
                throw new Error('Failed to check permission');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.checkProjectPermission error:', error);
            throw error;
        }
    },

    /**
     * Search users for sharing
     * @param {string} query - Search query (email or name)
     * @param {number} limit - Maximum results
     * @returns {Promise<Array>} Matching users
     */
    async searchUsers(query, limit = 10) {
        try {
            const params = new URLSearchParams({ q: query, limit });
            const response = await fetch(`/api/sharing/users/search?${params}`);

            if (!response.ok) {
                throw new Error('Failed to search users');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.searchUsers error:', error);
            throw error;
        }
    },

    /**
     * Get sharing activity log for a project
     * @param {number} projectId - Project ID
     * @returns {Promise<Array>} Activity log
     */
    async getProjectActivity(projectId) {
        try {
            const response = await fetch(`/api/sharing/projects/${projectId}/activity`);

            if (!response.ok) {
                throw new Error('Failed to get project activity');
            }

            return await response.json();
        } catch (error) {
            console.error('SharingClient.getProjectActivity error:', error);
            throw error;
        }
    },

    /**
     * Format permission level for display
     * @param {string} permission - Permission level
     * @returns {Object} Display info with icon and label
     */
    formatPermission(permission) {
        const permissions = {
            'read': {
                label: 'View Only',
                icon: 'fa-eye',
                color: 'secondary',
                description: 'Can view project but not make changes'
            },
            'write': {
                label: 'Can Edit',
                icon: 'fa-edit',
                color: 'primary',
                description: 'Can view and modify project'
            },
            'owner': {
                label: 'Owner',
                icon: 'fa-crown',
                color: 'warning',
                description: 'Full control including sharing and deletion'
            }
        };

        return permissions[permission] || permissions['read'];
    },

    /**
     * Check if user can perform action based on permission
     * @param {string} permission - User's permission level
     * @param {string} action - Action to check (read, write, delete, share)
     * @returns {boolean} Whether action is allowed
     */
    canPerformAction(permission, action) {
        const permissionLevels = {
            'read': ['read'],
            'write': ['read', 'write'],
            'owner': ['read', 'write', 'delete', 'share']
        };

        const allowed = permissionLevels[permission] || [];
        return allowed.includes(action);
    }
};

// Export for use in modules (if supported)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SharingClient;
}
