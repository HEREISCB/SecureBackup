// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize file upload form
    initializeFileUpload();
    
    // Initialize file rename form
    initializeRenameForm();
    
    // Initialize file delete confirmation
    initializeDeleteConfirmation();
    
    // Initialize restore version confirmation
    initializeRestoreVersionConfirmation();
    
    // Setup form validation
    setupFormValidation();
});

/**
 * Initializes tooltip functionality
 */
function initializeTooltips() {
    const tooltips = document.querySelectorAll('.tooltip');
    
    tooltips.forEach(tooltip => {
        const tooltipText = tooltip.querySelector('.tooltip-text');
        if (!tooltipText) return;
        
        tooltip.addEventListener('mouseenter', () => {
            tooltipText.style.visibility = 'visible';
            tooltipText.style.opacity = '1';
        });
        
        tooltip.addEventListener('mouseleave', () => {
            tooltipText.style.visibility = 'hidden';
            tooltipText.style.opacity = '0';
        });
    });
}

/**
 * Initializes file upload with progress indicator
 */
function initializeFileUpload() {
    const uploadForm = document.getElementById('upload-form');
    if (!uploadForm) return;
    
    const fileInput = document.getElementById('file');
    const fileLabel = document.querySelector('.custom-file-label');
    const progressContainer = document.createElement('div');
    progressContainer.className = 'upload-progress';
    progressContainer.style.display = 'none';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressContainer.appendChild(progressBar);
    
    uploadForm.appendChild(progressContainer);
    
    // Update file label with selected filename
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                if (fileLabel) {
                    fileLabel.textContent = fileName;
                }
            }
        });
    }
    
    // Handle form submission with progress
    uploadForm.addEventListener('submit', function(e) {
        if (fileInput && fileInput.files.length === 0) {
            e.preventDefault();
            showToast('Please select a file to upload', 'warning');
            return;
        }
        
        // Show progress bar
        progressContainer.style.display = 'block';
        
        // Simulate upload progress (in a real app, you'd use XMLHttpRequest or Fetch API for actual progress)
        simulateProgress(progressBar);
    });
}

/**
 * Simulates an upload progress for demonstration purposes
 * @param {HTMLElement} progressBar - The progress bar element
 */
function simulateProgress(progressBar) {
    let width = 0;
    const interval = setInterval(function() {
        if (width >= 90) {
            clearInterval(interval);
        } else {
            width += Math.random() * 10;
            progressBar.style.width = width + '%';
        }
    }, 300);
}

/**
 * Initializes the file rename form
 */
function initializeRenameForm() {
    const renameButtons = document.querySelectorAll('.rename-btn');
    const renameForm = document.getElementById('rename-form');
    const renameInput = document.getElementById('filename');
    const renameFileId = document.getElementById('rename-file-id');
    
    if (!renameForm || !renameInput || !renameFileId) return;
    
    renameButtons.forEach(button => {
        button.addEventListener('click', function() {
            const fileId = this.getAttribute('data-file-id');
            const fileName = this.getAttribute('data-file-name');
            
            // Set values in form
            renameInput.value = fileName;
            renameFileId.value = fileId;
            
            // Focus the input field
            renameInput.focus();
        });
    });
}

/**
 * Initializes confirmation dialogs for file deletion
 */
function initializeDeleteConfirmation() {
    const deleteButtons = document.querySelectorAll('.delete-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // For file version deletion with dynamic status update
            if (this.hasAttribute('data-version-id')) {
                e.preventDefault();
                const versionId = this.getAttribute('data-version-id');
                const versionNumber = this.getAttribute('data-version-number');
                
                // Confirm deletion
                if (confirm(`Are you sure you want to mark Version ${versionNumber} as deleted?`)) {
                    // Find the status element for this version
                    const statusElement = document.querySelector(`#version-${versionId} .version-status`);
                    if (statusElement) {
                        // Create or update the status badge
                        const existingBadge = statusElement.querySelector('.badge.bg-danger');
                        if (existingBadge) {
                            // If badge already exists, just animate it again
                            existingBadge.classList.remove('status-animation');
                            // Trigger reflow
                            void existingBadge.offsetWidth;
                            existingBadge.classList.add('status-animation');
                        } else {
                            // Remove any existing badges except Current Version
                            const oldBadges = statusElement.querySelectorAll('.badge');
                            oldBadges.forEach(badge => {
                                if (!badge.classList.contains('bg-success')) {
                                    badge.remove();
                                }
                            });
                            
                            // Create new badge
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-danger me-2 status-animation';
                            badge.innerHTML = '<i class="fas fa-trash me-1"></i>Deleted';
                            statusElement.appendChild(badge);
                        }
                        
                        // Show success notification
                        showToast(`Version ${versionNumber} marked as deleted`, 'danger');
                    }
                }
                return;
            }
            
            // For regular file deletion
            const fileName = this.getAttribute('data-file-name');
            if (!confirm(`Are you sure you want to delete "${fileName}"?`)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Initializes confirmation dialogs for version restoration
 */
function initializeRestoreVersionConfirmation() {
    // Handle existing backend restore buttons
    const restoreVersionButtons = document.querySelectorAll('.restore-version-btn');
    restoreVersionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const versionNumber = this.getAttribute('data-version-number');
            if (!confirm(`Are you sure you want to restore version ${versionNumber} as the current version?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Handle our new client-side restore buttons for status updates
    const restoreButtons = document.querySelectorAll('.restore-btn');
    restoreButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const versionId = this.getAttribute('data-version-id');
            const versionNumber = this.getAttribute('data-version-number');
            
            // Find the status element for this version
            const statusElement = document.querySelector(`#version-${versionId} .version-status`);
            if (statusElement) {
                // Create or update the status badge
                const existingBadge = statusElement.querySelector('.badge.bg-warning');
                if (existingBadge) {
                    // If badge already exists, just animate it again
                    existingBadge.classList.remove('status-animation');
                    // Trigger reflow
                    void existingBadge.offsetWidth;
                    existingBadge.classList.add('status-animation');
                } else {
                    // Remove any existing badges except Current Version
                    const oldBadges = statusElement.querySelectorAll('.badge');
                    oldBadges.forEach(badge => {
                        if (!badge.classList.contains('bg-success')) {
                            badge.remove();
                        }
                    });
                    
                    // Create new badge
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-warning me-2 status-animation';
                    badge.innerHTML = '<i class="fas fa-undo me-1"></i>Restored';
                    statusElement.appendChild(badge);
                }
                
                // Show success notification
                showToast(`Version ${versionNumber} marked as restored`, 'warning');
            }
        });
    });
}

/**
 * Sets up form validation for registration and login forms
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * Shows a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, warning, danger, etc.)
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create the toast
    const toastElement = document.createElement('div');
    toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
    toastElement.setAttribute('role', 'alert');
    toastElement.setAttribute('aria-live', 'assertive');
    toastElement.setAttribute('aria-atomic', 'true');
    
    // Create toast content
    toastElement.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toastElement);
    
    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
