// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize file search functionality
    initializeFileSearch();
    
    // Initialize sort functionality
    initializeFileSorting();
    
    // Add file size formatting
    formatFileSizes();
    
    // Initialize file preview
    initializeFilePreview();
});

/**
 * Initializes search functionality for files
 */
function initializeFileSearch() {
    const searchInput = document.getElementById('file-search');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const fileCards = document.querySelectorAll('.file-card');
        
        fileCards.forEach(card => {
            const fileName = card.querySelector('.file-name').textContent.toLowerCase();
            
            if (fileName.includes(searchTerm)) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
        
        // Show or hide empty state message
        const visibleFiles = Array.from(fileCards).filter(card => card.style.display !== 'none');
        const emptyState = document.querySelector('.empty-search-state');
        
        if (emptyState) {
            if (visibleFiles.length === 0 && searchTerm.length > 0) {
                emptyState.style.display = 'block';
            } else {
                emptyState.style.display = 'none';
            }
        }
    });
}

/**
 * Initializes sorting functionality for files
 */
function initializeFileSorting() {
    const sortDropdown = document.getElementById('sort-files');
    if (!sortDropdown) return;
    
    sortDropdown.addEventListener('change', function() {
        const sortBy = this.value;
        const filesContainer = document.querySelector('.files-container');
        const fileCards = Array.from(document.querySelectorAll('.file-card'));
        
        // Sort the file cards based on selected option
        fileCards.sort((a, b) => {
            switch (sortBy) {
                case 'name-asc':
                    return a.querySelector('.file-name').textContent.localeCompare(
                        b.querySelector('.file-name').textContent
                    );
                    
                case 'name-desc':
                    return b.querySelector('.file-name').textContent.localeCompare(
                        a.querySelector('.file-name').textContent
                    );
                    
                case 'date-asc':
                    return new Date(a.getAttribute('data-date')) - new Date(b.getAttribute('data-date'));
                    
                case 'date-desc':
                    return new Date(b.getAttribute('data-date')) - new Date(a.getAttribute('data-date'));
                    
                case 'size-asc':
                    return parseInt(a.getAttribute('data-size')) - parseInt(b.getAttribute('data-size'));
                    
                case 'size-desc':
                    return parseInt(b.getAttribute('data-size')) - parseInt(a.getAttribute('data-size'));
                    
                default:
                    return 0;
            }
        });
        
        // Remove all file cards
        fileCards.forEach(card => card.remove());
        
        // Append sorted cards
        fileCards.forEach(card => filesContainer.appendChild(card));
    });
}

/**
 * Formats file sizes to human-readable format
 */
function formatFileSizes() {
    const fileSizes = document.querySelectorAll('.file-size');
    
    fileSizes.forEach(sizeElement => {
        const sizeInBytes = parseInt(sizeElement.getAttribute('data-size'));
        sizeElement.textContent = formatBytes(sizeInBytes);
    });
}

/**
 * Formats bytes to a human-readable format
 * @param {number} bytes - The size in bytes
 * @param {number} decimals - The number of decimal places
 * @returns {string} - The formatted size
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Initializes file preview functionality
 */
function initializeFilePreview() {
    const previewButtons = document.querySelectorAll('.preview-btn');
    
    previewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const fileId = this.getAttribute('data-file-id');
            const fileName = this.getAttribute('data-file-name');
            const fileType = this.getAttribute('data-file-type');
            
            // Get file extension
            const extension = fileName.split('.').pop().toLowerCase();
            
            // Check if file is previewable
            if (isPreviewable(extension)) {
                // In a real implementation, you would fetch the file content from the server
                // For now, we'll just show a modal indicating that preview is available
                showPreviewModal(fileName, fileType);
            } else {
                // Show message that preview is not available
                alert(`Preview not available for ${extension} files. Please download the file to view it.`);
            }
        });
    });
}

/**
 * Checks if a file is previewable based on its extension
 * @param {string} extension - The file extension
 * @returns {boolean} - Whether the file is previewable
 */
function isPreviewable(extension) {
    const previewableExtensions = ['txt', 'pdf', 'jpg', 'jpeg', 'png', 'gif'];
    return previewableExtensions.includes(extension);
}

/**
 * Shows a preview modal for a file
 * @param {string} fileName - The name of the file
 * @param {string} fileType - The MIME type of the file
 */
function showPreviewModal(fileName, fileType) {
    // Create modal element
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'previewModal';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-labelledby', 'previewModalLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    // Create modal content
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="previewModalLabel">Preview: ${fileName}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body text-center">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        This is a preview placeholder. In a complete implementation, the actual file content would be displayed here.
                    </div>
                    <div class="preview-placeholder d-flex align-items-center justify-content-center" style="height: 300px; background-color: #f8f9fa;">
                        <div class="text-center">
                            <i class="fas fa-file fa-3x mb-3"></i>
                            <h4>${fileName}</h4>
                            <p class="text-muted">${fileType}</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <a href="#" class="btn btn-primary">Download</a>
                </div>
            </div>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(modal);
    
    // Show modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    // Remove modal from DOM after it's hidden
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
}
