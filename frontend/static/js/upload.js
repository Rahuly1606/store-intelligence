/**
 * Upload Page JavaScript
 * Handles video upload and processing
 */

$(document).ready(function() {
    const uploadForm = $('#uploadForm');
    const uploadBtn = $('#uploadBtn');
    const progressSection = $('#progressSection');
    const progressBar = $('#progressBar');
    const statusText = $('#statusText');
    const resultSection = $('#resultSection');
    const resultAlert = $('#resultAlert');

    // Handle form submission
    uploadForm.on('submit', function(e) {
        e.preventDefault();
        
        // Validate file
        const fileInput = $('#videoFile')[0];
        if (!fileInput.files || fileInput.files.length === 0) {
            showError('Please select a video file');
            return;
        }

        const file = fileInput.files[0];
        const maxSize = 500 * 1024 * 1024; // 500MB
        
        if (file.size > maxSize) {
            showError('File size exceeds 500MB limit');
            return;
        }

        // Start upload
        uploadAndProcess();
    });

    function uploadAndProcess() {
        // Disable form
        uploadBtn.prop('disabled', true);
        uploadForm.find('input, select').prop('disabled', true);
        
        // Show progress
        resultSection.hide();
        progressSection.show();
        updateProgress(10, 'Uploading video...');

        // Prepare form data manually to ensure file is included
        const formData = new FormData();
        const fileInput = $('#videoFile')[0];
        const cameraType = $('#cameraType').val();
        const storeId = $('#storeId').val();
        
        formData.append('file', fileInput.files[0]);
        formData.append('camera_type', cameraType);
        formData.append('store_id', storeId);

        // Upload and process
        $.ajax({
            url: '/api/upload-and-process',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function() {
                const xhr = new window.XMLHttpRequest();
                // Upload progress
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 50; // 50% for upload
                        updateProgress(percentComplete, 'Uploading video...');
                    }
                }, false);
                return xhr;
            },
            success: function(response) {
                if (response.success) {
                    updateProgress(100, 'Processing complete!');
                    showSuccess(response.message, response.data);
                } else {
                    showError(response.error || 'Processing failed');
                }
            },
            error: function(xhr) {
                let errorMsg = 'Upload failed';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                showError(errorMsg);
            },
            complete: function() {
                // Re-enable form
                uploadBtn.prop('disabled', false);
                uploadForm.find('input, select').prop('disabled', false);
            }
        });

        // Simulate processing progress (since we can't track actual pipeline progress)
        let progress = 50;
        const progressInterval = setInterval(function() {
            if (progress < 90) {
                progress += 5;
                updateProgress(progress, 'Processing video through detection pipeline...');
            } else {
                clearInterval(progressInterval);
            }
        }, 2000);
    }

    function updateProgress(percent, message) {
        progressBar.css('width', percent + '%');
        progressBar.attr('aria-valuenow', percent);
        statusText.text(message);
    }

    function showSuccess(message, data) {
        progressSection.hide();
        resultAlert.html(`
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <h5 class="alert-heading"><i class="bi bi-check-circle"></i> Success!</h5>
                <p>${message}</p>
                <hr>
                <p class="mb-0">
                    <strong>Filename:</strong> ${data.filename}<br>
                    <strong>Camera:</strong> ${data.camera_type}<br>
                    <strong>Status:</strong> ${data.status}
                </p>
                <div class="mt-3">
                    <a href="/dashboard?store_id=${data.store_id}" class="btn btn-primary">
                        <i class="bi bi-graph-up"></i> View Dashboard
                    </a>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        resultSection.show();
        
        // Reset form
        uploadForm[0].reset();
    }

    function showError(message) {
        progressSection.hide();
        resultAlert.html(`
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <h5 class="alert-heading"><i class="bi bi-exclamation-triangle"></i> Error</h5>
                <p>${message}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        resultSection.show();
    }
});
