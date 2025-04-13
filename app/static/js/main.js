// Main JavaScript for Invoice OCR Application

$(document).ready(function() {
    // Global variables
    let selectedFiles = [];
    let sessionId = null;
    let selectedEngine = 'baidu';
    let selectedFile = null; // Currently selected file for export
    
    // Initialize UI
    initializeUI();
    
    // Event Handlers
    function initializeUI() {
        // Initialize tooltips
        initializeTooltips();
        
        // Initialize file input
        $('#selectFilesBtn').click(function() {
            $('#fileInput').click();
        });
        
        $('#fileInput').change(handleFileSelect);
        
        // Initialize drag and drop
        const dropZone = document.getElementById('dropZone');
        
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).addClass('dragover');
        });
        
        dropZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).removeClass('dragover');
        });
        
        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).removeClass('dragover');
            
            const files = e.dataTransfer.files;
            handleFiles(files);
        });
        
        // Initialize engine selection
        $('.engine-option').click(function() {
            $('.engine-option').removeClass('selected');
            $(this).addClass('selected');
            selectedEngine = $(this).data('engine');
            
            showAlert(`OCR engine changed to ${$(this).find('h6').text()}`, 'info');
        });
        
        // Set default engine
        $('.engine-option[data-engine="baidu"]').addClass('selected');
        
        // Initialize process button
        $('#processBtn').click(processFiles);
        
        // Initialize export buttons
        $('.export-btn').click(function() {
            if (!selectedFile) {
                showAlert('Please select a file to export', 'warning');
                return;
            }
            
            const format = $(this).data('format');
            exportResults(selectedFile, format);
        });
    }
    
    // Initialize Bootstrap tooltips
    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Handle file selection
    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }
    
    function handleFiles(files) {
        // Check file types
        const validFiles = Array.from(files).filter(file => {
            const extension = file.name.split('.').pop().toLowerCase();
            return ['png', 'jpg', 'jpeg', 'pdf', 'tif', 'tiff'].includes(extension);
        });
        
        if (validFiles.length === 0) {
            showAlert('No valid files selected. Supported formats: PNG, JPG, JPEG, PDF, TIF, TIFF', 'danger');
            return;
        }
        
        // Check quantity
        if (validFiles.length > 10) {
            showAlert('Maximum 10 files can be processed at once', 'warning');
            return;
        }
        
        // Store selected files
        selectedFiles = validFiles;
        
        // Update UI
        updateFileList();
        
        // Enable process button
        $('#processBtn').prop('disabled', false);
        
        showAlert(`${validFiles.length} files ready for processing`, 'success');
    }
    
    // Update file list in UI
    function updateFileList() {
        // Add file list container if it doesn't exist
        if ($('#fileList').length === 0) {
            $('#dropZone').after('<div id="fileList" class="mt-3"></div>');
        }
        
        // Clear and rebuild file list
        $('#fileList').empty();
        
        selectedFiles.forEach((file, index) => {
            const fileItem = $(`
                <div class="file-item">
                    <i class="far fa-file"></i>
                    <span class="file-name">${file.name}</span>
                    <i class="fas fa-times remove-file" data-index="${index}"></i>
                </div>
            `);
            
            $('#fileList').append(fileItem);
        });
        
        // Add remove handlers
        $('.remove-file').click(function() {
            const index = $(this).data('index');
            selectedFiles.splice(index, 1);
            updateFileList();
            
            if (selectedFiles.length === 0) {
                $('#processBtn').prop('disabled', true);
                $('#fileList').remove();
            }
        });
    }
    
    // Process the selected files
    function processFiles() {
        // Check if files are selected
        if (selectedFiles.length === 0) {
            showAlert('Please select files to process', 'warning');
            return;
        }
        
        // Clear downloads section
        $('#downloadsList').empty();
        $('#downloadsSection').addClass('d-none');
        
        // Prepare form data
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files[]', file);
        });
        
        // Show processing indicator
        $('#noResultsPlaceholder').addClass('d-none');
        $('#ocrResults').addClass('d-none');
        $('#processingIndicator').removeClass('d-none');
        $('#processBtn').prop('disabled', true);
        
        // Hide export options
        $('#exportOptions').addClass('d-none');
        
        // Upload files
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                if (response.success) {
                    sessionId = response.session_id;
                    processOCR();
                } else {
                    handleError(response.error);
                }
            },
            error: function(xhr) {
                handleError('File upload failed: ' + xhr.responseText);
            }
        });
    }
    
    // Process OCR after files are uploaded
    function processOCR() {
        const invoiceType = $('input[name="invoiceType"]:checked').val();
        
        $.ajax({
            url: '/process',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                session_id: sessionId,
                engine: selectedEngine,
                invoice_type: invoiceType
            }),
            success: function(response) {
                // Hide processing indicator
                $('#processingIndicator').addClass('d-none');
                
                if (response.success) {
                    displayResults(response.results);
                } else {
                    handleError(response.error);
                }
                
                // Re-enable process button
                $('#processBtn').prop('disabled', false);
            },
            error: function(xhr) {
                handleError('OCR processing failed: ' + xhr.responseText);
                $('#processBtn').prop('disabled', false);
            }
        });
    }
    
    // Display OCR results
    function displayResults(results) {
        // Clear previous results
        $('#ocrResults').empty().removeClass('d-none');
        
        if (results.length === 0) {
            $('#ocrResults').html('<div class="alert alert-info">No results to display</div>');
            return;
        }
        
        // Add result cards
        results.forEach(result => {
            const cardClass = result.success ? 'result-card' : 'result-card error';
            const statusBadge = result.success 
                ? `<span class="badge bg-success">Success</span>`
                : `<span class="badge bg-danger">Failed</span>`;
            
            const engineBadge = `<span class="badge bg-secondary">${result.engine}</span>`;
            
            let cardContent = '';
            
            if (result.success) {
                // Display preview
                let previewText = '';
                if (result.preview && result.preview.length > 0) {
                    previewText = result.preview.join('\n');
                } else {
                    previewText = 'No text detected';
                }
                
                cardContent = `
                    <div class="preview-text">${previewText}</div>
                    <div class="mt-3">
                        <button class="btn btn-sm btn-primary select-file-btn" data-filename="${result.filename}">
                            Select for Export
                        </button>
                    </div>
                `;
            } else {
                // Display error
                cardContent = `
                    <div class="alert alert-danger">${result.error || 'Unknown error'}</div>
                `;
            }
            
            const card = $(`
                <div class="${cardClass}">
                    <div class="card-header">
                        <strong>${result.filename}</strong>
                        <div>
                            ${engineBadge}
                            ${statusBadge}
                        </div>
                    </div>
                    <div class="card-body">
                        ${cardContent}
                    </div>
                </div>
            `);
            
            $('#ocrResults').append(card);
        });
        
        // Add file selection handler
        $('.select-file-btn').click(function() {
            selectedFile = $(this).data('filename');
            $('.select-file-btn').removeClass('btn-success').addClass('btn-primary').text('Select for Export');
            $(this).removeClass('btn-primary').addClass('btn-success').text('Selected ✓');
            
            // Show export options
            $('#exportOptions').removeClass('d-none');
            
            showAlert(`File "${selectedFile}" selected for export`, 'info');
        });
        
        // Select first successful result automatically
        const firstSuccess = results.find(r => r.success);
        if (firstSuccess) {
            selectedFile = firstSuccess.filename;
            $('#exportOptions').removeClass('d-none');
            $(`button[data-filename="${selectedFile}"]`)
                .removeClass('btn-primary')
                .addClass('btn-success')
                .text('Selected ✓');
        }
    }
    
    // Export results
    function exportResults(filename, format) {
        // Show processing notification
        showAlert(`Exporting ${filename} to ${format.toUpperCase()}...`, 'info');
        
        $.ajax({
            url: '/export',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                session_id: sessionId,
                filename: filename,
                format: format
            }),
            success: function(response) {
                if (response.success) {
                    // Add to downloads section
                    addDownload(response.filename, response.download_url, format);
                    showAlert(`Export complete! File ready for download.`, 'success');
                } else {
                    handleError(response.error);
                }
            },
            error: function(xhr) {
                handleError('Export failed: ' + xhr.responseText);
            }
        });
    }
    
    // Add a download to the downloads section
    function addDownload(filename, url, format) {
        // Show downloads section if hidden
        $('#downloadsSection').removeClass('d-none');
        
        // Determine icon based on format
        let icon = 'fa-file';
        let colorClass = 'text-secondary';
        
        if (format === 'xlsx') {
            icon = 'fa-file-excel';
            colorClass = 'text-success';
        } else if (format === 'docx') {
            icon = 'fa-file-word';
            colorClass = 'text-primary';
        } else if (format === 'txt') {
            icon = 'fa-file-alt';
            colorClass = 'text-secondary';
        }
        
        // Create download item
        const downloadItem = $(`
            <li class="download-item">
                <i class="far ${icon} ${colorClass}"></i>
                <span class="download-name">${filename}</span>
                <a href="${url}" class="btn btn-sm btn-outline-primary" download>
                    <i class="fas fa-download"></i> Download
                </a>
            </li>
        `);
        
        // Add to list
        $('#downloadsList').prepend(downloadItem);
    }
    
    // Error handling
    function handleError(message) {
        $('#processingIndicator').addClass('d-none');
        showAlert(message, 'danger');
        console.error(message);
    }
    
    // Show alert
    function showAlert(message, type = 'info') {
        const alert = $(`
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `);
        
        $('#alertContainer').append(alert);
        
        // Auto close after 5 seconds
        setTimeout(() => {
            alert.alert('close');
        }, 5000);
    }
}); 