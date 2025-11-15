/**
 * UI Utilities for Grading App
 *
 * Provides reusable notification, loading, and confirmation dialog functionality.
 */

class UIUtils {
    constructor() {
        this.toastContainer = null;
        this.loadingOverlay = null;
        this.init();
    }

    init() {
        // Create toast container
        this.createToastContainer();
        // Create loading overlay
        this.createLoadingOverlay();
        // Create confirmation modal
        this.createConfirmationModal();
    }

    /**
     * Create Bootstrap toast container
     */
    createToastContainer() {
        if (document.querySelector('.toast-container')) return;

        const container = document.createElement('div');
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        this.toastContainer = container;
    }

    /**
     * Create loading overlay
     */
    createLoadingOverlay() {
        if (document.getElementById('loadingOverlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'd-none';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9998;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        overlay.innerHTML = `
            <div class="spinner-border text-light" style="width: 3rem; height: 3rem;" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        `;
        document.body.appendChild(overlay);
        this.loadingOverlay = overlay;
    }

    /**
     * Create confirmation modal
     */
    createConfirmationModal() {
        if (document.getElementById('confirmationModal')) return;

        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'confirmationModal';
        modal.tabIndex = '-1';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmationModalTitle">Confirm Action</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="confirmationModalBody">
                        Are you sure you want to proceed?
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-danger" id="confirmationModalConfirm">Confirm</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    /**
     * Show a notification toast
     * @param {string} message - The message to display
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {number} duration - Auto-hide duration in milliseconds (0 = no auto-hide)
     */
    showNotification(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        // Determine icon and color based on type
        const config = {
            success: { icon: 'fa-check-circle', bgClass: 'bg-success', title: 'Success' },
            error: { icon: 'fa-exclamation-circle', bgClass: 'bg-danger', title: 'Error' },
            warning: { icon: 'fa-exclamation-triangle', bgClass: 'bg-warning', title: 'Warning' },
            info: { icon: 'fa-info-circle', bgClass: 'bg-primary', title: 'Info' }
        };

        const { icon, bgClass, title } = config[type] || config.info;

        toast.innerHTML = `
            <div class="toast-header ${bgClass} text-white">
                <i class="fas ${icon} me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${this.escapeHtml(message)}
            </div>
        `;

        this.toastContainer.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, {
            autohide: duration > 0,
            delay: duration
        });

        bsToast.show();

        // Remove from DOM after hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });

        return bsToast;
    }

    /**
     * Show success notification
     */
    success(message, duration = 5000) {
        return this.showNotification(message, 'success', duration);
    }

    /**
     * Show error notification
     */
    error(message, duration = 7000) {
        return this.showNotification(message, 'error', duration);
    }

    /**
     * Show warning notification
     */
    warning(message, duration = 6000) {
        return this.showNotification(message, 'warning', duration);
    }

    /**
     * Show info notification
     */
    info(message, duration = 5000) {
        return this.showNotification(message, 'info', duration);
    }

    /**
     * Show loading overlay
     * @param {string} message - Optional message to display
     */
    showLoading(message = 'Loading...') {
        if (message !== 'Loading...') {
            const spinnerContainer = this.loadingOverlay.querySelector('.spinner-border');
            const existingText = this.loadingOverlay.querySelector('.loading-text');
            if (existingText) {
                existingText.textContent = message;
            } else {
                const text = document.createElement('div');
                text.className = 'loading-text text-white mt-3 fw-bold';
                text.textContent = message;
                spinnerContainer.parentElement.appendChild(text);
            }
        }
        this.loadingOverlay.classList.remove('d-none');
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        this.loadingOverlay.classList.add('d-none');
    }

    /**
     * Show confirmation dialog
     * @param {string} message - The confirmation message
     * @param {string} title - The dialog title
     * @param {string} confirmText - Text for confirm button (default: 'Confirm')
     * @param {string} variant - Bootstrap variant for confirm button (default: 'danger')
     * @returns {Promise<boolean>} - Resolves to true if confirmed, false if cancelled
     */
    confirm(message, title = 'Confirm Action', confirmText = 'Confirm', variant = 'danger') {
        return new Promise((resolve) => {
            const modal = document.getElementById('confirmationModal');
            const modalTitle = document.getElementById('confirmationModalTitle');
            const modalBody = document.getElementById('confirmationModalBody');
            const confirmBtn = document.getElementById('confirmationModalConfirm');

            // Update content
            modalTitle.textContent = title;
            modalBody.innerHTML = this.escapeHtml(message);
            confirmBtn.textContent = confirmText;
            confirmBtn.className = `btn btn-${variant}`;

            // Create Bootstrap modal instance
            const bsModal = new bootstrap.Modal(modal);

            // Handle confirm
            const handleConfirm = () => {
                bsModal.hide();
                resolve(true);
                cleanup();
            };

            // Handle cancel
            const handleCancel = () => {
                resolve(false);
                cleanup();
            };

            // Cleanup listeners
            const cleanup = () => {
                confirmBtn.removeEventListener('click', handleConfirm);
                modal.removeEventListener('hidden.bs.modal', handleCancel);
            };

            // Attach listeners
            confirmBtn.addEventListener('click', handleConfirm);
            modal.addEventListener('hidden.bs.modal', handleCancel, { once: true });

            // Show modal
            bsModal.show();
        });
    }

    /**
     * Show inline error message on form field
     * @param {HTMLElement} field - The form field element
     * @param {string} message - The error message
     */
    showFieldError(field, message) {
        // Remove existing error
        this.clearFieldError(field);

        // Add error class
        field.classList.add('is-invalid');

        // Create error feedback element
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        field.parentElement.appendChild(feedback);
    }

    /**
     * Clear error message from form field
     * @param {HTMLElement} field - The form field element
     */
    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const feedback = field.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    /**
     * Clear all field errors in a form
     * @param {HTMLElement} form - The form element
     */
    clearFormErrors(form) {
        form.querySelectorAll('.is-invalid').forEach(field => {
            this.clearFieldError(field);
        });
    }

    /**
     * Handle API errors with user-friendly messages
     * @param {Error|Response} error - The error object or response
     * @param {string} fallbackMessage - Fallback message if error parsing fails
     */
    async handleApiError(error, fallbackMessage = 'An unexpected error occurred') {
        let errorMessage = fallbackMessage;

        if (error instanceof Response) {
            try {
                const data = await error.json();
                errorMessage = data.error || data.message || fallbackMessage;
            } catch (e) {
                errorMessage = `Server error (${error.status}): ${error.statusText}`;
            }
        } else if (error instanceof Error) {
            errorMessage = error.message || fallbackMessage;
        } else if (typeof error === 'string') {
            errorMessage = error;
        }

        this.error(errorMessage);
        return errorMessage;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} - Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Disable a button and show loading state
     * @param {HTMLElement} button - The button element
     * @param {string} loadingText - Text to show while loading (default: 'Loading...')
     * @returns {Function} - Function to restore button state
     */
    setButtonLoading(button, loadingText = 'Loading...') {
        const originalText = button.innerHTML;
        const originalDisabled = button.disabled;

        button.disabled = true;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            ${loadingText}
        `;

        // Return function to restore button
        return () => {
            button.disabled = originalDisabled;
            button.innerHTML = originalText;
        };
    }

    /**
     * Validate form field with custom validation
     * @param {HTMLElement} field - The form field
     * @param {Function} validator - Validation function returning true/false or error message string
     * @returns {boolean} - True if valid
     */
    validateField(field, validator) {
        this.clearFieldError(field);

        const result = validator(field.value, field);

        if (result === true) {
            field.classList.add('is-valid');
            return true;
        }

        const errorMessage = typeof result === 'string' ? result : 'Invalid value';
        this.showFieldError(field, errorMessage);
        return false;
    }
}

// Create global instance
const ui = new UIUtils();
