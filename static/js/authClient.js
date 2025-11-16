/**
 * Authentication API Client
 * Provides methods to interact with authentication endpoints
 */

const AuthClient = {
    /**
     * Login with email and password
     * @param {string} email - User email
     * @param {string} password - User password
     * @param {boolean} remember - Remember me flag
     * @returns {Promise<Object>} Login response with user data
     */
    async login(email, password, remember = false) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password, remember })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Login failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.login error:', error);
            throw error;
        }
    },

    /**
     * Register a new user
     * @param {Object} userData - User registration data
     * @param {string} userData.email - User email
     * @param {string} userData.password - User password
     * @param {string} userData.display_name - User display name
     * @returns {Promise<Object>} Registration response
     */
    async register(userData) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Registration failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.register error:', error);
            throw error;
        }
    },

    /**
     * Logout current user
     * @returns {Promise<Object>} Logout response
     */
    async logout() {
        try {
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Logout failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.logout error:', error);
            throw error;
        }
    },

    /**
     * Get current user information
     * @returns {Promise<Object>} Current user data
     */
    async getCurrentUser() {
        try {
            const response = await fetch('/api/auth/me');

            if (!response.ok) {
                if (response.status === 401) {
                    return null; // Not authenticated
                }
                throw new Error('Failed to get current user');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.getCurrentUser error:', error);
            throw error;
        }
    },

    /**
     * Request password reset
     * @param {string} email - User email
     * @returns {Promise<Object>} Reset request response
     */
    async requestPasswordReset(email) {
        try {
            const response = await fetch('/api/auth/request-reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Reset request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.requestPasswordReset error:', error);
            throw error;
        }
    },

    /**
     * Reset password with token
     * @param {string} token - Reset token
     * @param {string} password - New password
     * @returns {Promise<Object>} Reset response
     */
    async resetPassword(token, password) {
        try {
            const response = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Password reset failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.resetPassword error:', error);
            throw error;
        }
    },

    /**
     * Update current user profile
     * @param {Object} profileData - Profile update data
     * @returns {Promise<Object>} Updated user data
     */
    async updateProfile(profileData) {
        try {
            const response = await fetch('/api/auth/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(profileData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Profile update failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.updateProfile error:', error);
            throw error;
        }
    },

    /**
     * Change password for current user
     * @param {string} currentPassword - Current password
     * @param {string} newPassword - New password
     * @returns {Promise<Object>} Password change response
     */
    async changePassword(currentPassword, newPassword) {
        try {
            const response = await fetch('/api/auth/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Password change failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.changePassword error:', error);
            throw error;
        }
    },

    /**
     * Get all users (admin only)
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} Users list with pagination
     */
    async getUsers(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `/api/auth/users${queryString ? '?' + queryString : ''}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to get users');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.getUsers error:', error);
            throw error;
        }
    },

    /**
     * Create a new user (admin only)
     * @param {Object} userData - User creation data
     * @returns {Promise<Object>} Created user data
     */
    async createUser(userData) {
        try {
            const response = await fetch('/api/auth/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'User creation failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.createUser error:', error);
            throw error;
        }
    },

    /**
     * Update a user (admin only)
     * @param {number} userId - User ID
     * @param {Object} userData - User update data
     * @returns {Promise<Object>} Updated user data
     */
    async updateUser(userId, userData) {
        try {
            const response = await fetch(`/api/auth/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'User update failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.updateUser error:', error);
            throw error;
        }
    },

    /**
     * Delete a user (admin only)
     * @param {number} userId - User ID
     * @returns {Promise<Object>} Deletion response
     */
    async deleteUser(userId) {
        try {
            const response = await fetch(`/api/auth/users/${userId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'User deletion failed');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.deleteUser error:', error);
            throw error;
        }
    },

    /**
     * Get user sessions
     * @returns {Promise<Array>} List of active sessions
     */
    async getSessions() {
        try {
            const response = await fetch('/api/auth/sessions');

            if (!response.ok) {
                throw new Error('Failed to get sessions');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.getSessions error:', error);
            throw error;
        }
    },

    /**
     * Revoke a session
     * @param {string} sessionId - Session ID to revoke
     * @returns {Promise<Object>} Revocation response
     */
    async revokeSession(sessionId) {
        try {
            const response = await fetch(`/api/auth/sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to revoke session');
            }

            return await response.json();
        } catch (error) {
            console.error('AuthClient.revokeSession error:', error);
            throw error;
        }
    },

    /**
     * Validate password strength
     * @param {string} password - Password to validate
     * @returns {Object} Strength score and feedback
     */
    validatePasswordStrength(password) {
        const result = {
            score: 0,
            feedback: [],
            level: 'weak'
        };

        if (!password) {
            result.feedback.push('Password is required');
            return result;
        }

        // Length check
        if (password.length >= 8) {
            result.score += 20;
        } else {
            result.feedback.push('At least 8 characters required');
        }

        // Uppercase check
        if (/[A-Z]/.test(password)) {
            result.score += 20;
        } else {
            result.feedback.push('Include uppercase letters');
        }

        // Lowercase check
        if (/[a-z]/.test(password)) {
            result.score += 20;
        } else {
            result.feedback.push('Include lowercase letters');
        }

        // Number check
        if (/\d/.test(password)) {
            result.score += 20;
        } else {
            result.feedback.push('Include numbers');
        }

        // Special character check
        if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
            result.score += 20;
        } else {
            result.feedback.push('Include special characters');
        }

        // Determine level
        if (result.score >= 80) {
            result.level = 'strong';
        } else if (result.score >= 60) {
            result.level = 'medium';
        } else {
            result.level = 'weak';
        }

        return result;
    }
};

// Export for use in modules (if supported)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthClient;
}
