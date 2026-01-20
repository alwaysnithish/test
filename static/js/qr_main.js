/**
 * QR Tools JavaScript - Enhanced Implementation
 * Handles QR code generation, file uploads, and scanning
 */

// Global variables
let currentFile = null;
let cameraStream = null;
let scanningInterval = null;

// CSRF Token Handler
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

// Tab switching
function switchQRTab(tab) {
    // Remove active from all tabs and content
    document.querySelectorAll('.qr-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.qr-content').forEach(c => c.classList.remove('active'));
    
    // Find and activate the clicked tab
    const clickedTab = Array.from(document.querySelectorAll('.qr-tab')).find(
        t => t.textContent.toLowerCase().includes(tab === 'generator' ? 'generate' : 'scan')
    );
    if (clickedTab) clickedTab.classList.add('active');
    
    // Activate corresponding content
    document.getElementById('qr-' + tab).classList.add('active');
    
    // Stop camera if switching away from scanner
    if (tab !== 'scanner') {
        stopCamera();
    }
}

// Alert functions
function showAlert(type, message) {
    const alert = document.getElementById(type + '-alert');
    const isSuccess = message.toLowerCase().includes('success') || 
                     message.toLowerCase().includes('ready');
    
    alert.className = `qr-alert qr-alert-${isSuccess ? 'success' : 'error'} show`;
    alert.innerHTML = `<i class="fas fa-${isSuccess ? 'check-circle' : 'exclamation-triangle'}"></i>${message}`;
    
    setTimeout(() => {
        alert.classList.remove('show');
    }, 5000);
}

// Generate QR from text/URL
async function generateTextQR() {
    const text = document.getElementById('qr-text').value.trim();
    
    if (!text) {
        showAlert('gen', 'Please enter text or URL to generate QR code');
        return;
    }

    if (text.length > 4296) {
        showAlert('gen', 'Text too long! Maximum 4,296 characters allowed');
        return;
    }

    const size = document.getElementById('qr-size').value;
    const errorCorrection = document.getElementById('qr-error').value;

    document.getElementById('gen-loading').classList.add('show');
    
    try {
        const response = await fetch('/qrcodeandscanner/api/generate-qr/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                data: text,
                size: size,
                error_correction: errorCorrection
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to generate QR code');
        }

        const result = await response.json();

        if (result.success) {
            displayQRCode(result.qr_image, text);
            showAlert('gen', 'QR code generated successfully!');
        } else {
            showAlert('gen', result.error || 'Failed to generate QR code');
        }
    } catch (error) {
        console.error('Generation error:', error);
        showAlert('gen', 'Error: ' + error.message);
    } finally {
        document.getElementById('gen-loading').classList.remove('show');
    }
}

// File selection handler
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    currentFile = file;

    // Validate file size
    if (file.size > 10 * 1024 * 1024) {
        showAlert('gen', 'File size exceeds 10MB limit');
        currentFile = null;
        return;
    }

    // Display file info
    const fileInfo = document.getElementById('file-info');
    fileInfo.innerHTML = `
        <div class="qr-file-info-item">
            <span class="qr-file-info-label"><i class="fas fa-file"></i> File Name:</span>
            <span class="qr-file-info-value">${file.name}</span>
        </div>
        <div class="qr-file-info-item">
            <span class="qr-file-info-label"><i class="fas fa-hdd"></i> File Size:</span>
            <span class="qr-file-info-value">${(file.size / 1024).toFixed(2)} KB</span>
        </div>
        <div class="qr-file-info-item">
            <span class="qr-file-info-label"><i class="fas fa-tag"></i> File Type:</span>
            <span class="qr-file-info-value">${file.type}</span>
        </div>
    `;
    fileInfo.style.display = 'block';

    document.getElementById('upload-btn').disabled = false;
    showAlert('gen', 'File selected successfully! Click "Upload & Generate QR Code" to continue');
}

// Upload file and generate QR
async function uploadFileAndGenerateQR() {
    if (!currentFile) {
        showAlert('gen', 'Please select a file first');
        return;
    }

    const uploadBtn = document.getElementById('upload-btn');
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

    document.getElementById('gen-loading').classList.add('show');

    try {
        const formData = new FormData();
        formData.append('file', currentFile);

        const response = await fetch('/qrcodeandscanner/api/upload-file/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Upload failed');
        }

        const result = await response.json();

        if (result.success) {
            displayQRCode(result.qr_image, result.file_url);
            showAlert('gen', 'File uploaded successfully! QR code links to: ' + result.file_name);
        } else {
            showAlert('gen', result.error || 'Failed to upload file');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('gen', 'Error: ' + error.message);
    } finally {
        document.getElementById('gen-loading').classList.remove('show');
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload & Generate QR Code';
    }
}

// Display QR code
function displayQRCode(imageData, data) {
    const resultDiv = document.getElementById('qr-result');
    const qrImage = document.getElementById('qr-image');
    const qrDataDisplay = document.getElementById('qr-data-display');
    
    qrImage.src = imageData;
    qrDataDisplay.innerHTML = '<strong><i class="fas fa-info-circle"></i> Encoded Data:</strong><br>' + 
        (data.length > 100 ? data.substring(0, 100) + '...' : data);
    resultDiv.classList.add('show');
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Download QR code
function downloadQR() {
    const qrImage = document.getElementById('qr-image');
    const link = document.createElement('a');
    link.href = qrImage.src;
    link.download = 'qr-code-21ktools.png';
    link.click();
    
    showAlert('gen', 'QR code downloaded successfully!');
}

// Reset generator
function resetGenerator() {
    document.getElementById('qr-text').value = '';
    document.getElementById('file-input').value = '';
    document.getElementById('file-info').style.display = 'none';
    document.getElementById('qr-result').classList.remove('show');
    document.getElementById('upload-btn').disabled = true;
    currentFile = null;
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Camera scanning
async function startCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'environment' } 
        });
        
        const video = document.getElementById('video-preview');
        video.srcObject = cameraStream;
        video.classList.add('show');
        
        showAlert('scan', 'Camera started successfully! Point at a QR code to scan');
        
        // Start scanning
        scanningInterval = setInterval(scanFromCamera, 500);
        
    } catch (error) {
        console.error('Camera error:', error);
        showAlert('scan', 'Camera access denied or not available. Please check permissions.');
    }
}

function scanFromCamera() {
    const video = document.getElementById('video-preview');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        
        if (code) {
            displayScanResult(code.data);
            stopCamera();
            showAlert('scan', 'QR code scanned successfully!');
        }
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    if (scanningInterval) {
        clearInterval(scanningInterval);
        scanningInterval = null;
    }
    
    const video = document.getElementById('video-preview');
    video.classList.remove('show');
    video.srcObject = null;
}

// Scan uploaded QR image
function scanUploadedImage(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            const canvas = document.getElementById('canvas');
            const context = canvas.getContext('2d');
            
            canvas.width = img.width;
            canvas.height = img.height;
            context.drawImage(img, 0, 0);
            
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(imageData.data, imageData.width, imageData.height);
            
            if (code) {
                displayScanResult(code.data);
                showAlert('scan', 'QR code scanned successfully from image!');
            } else {
                showAlert('scan', 'No QR code found in the image. Please try another image.');
            }
        };
        img.src = e.target.result;
    };
    
    reader.readAsDataURL(file);
}

// Display scan result
function displayScanResult(data) {
    const resultDiv = document.getElementById('scanner-result');
    const resultText = document.getElementById('scan-result-text');
    const openUrlBtn = document.getElementById('open-url-btn');
    
    resultText.textContent = data;
    resultDiv.classList.add('show');
    
    // Show "Open URL" button if result is a URL
    if (data.startsWith('http://') || data.startsWith('https://')) {
        openUrlBtn.style.display = 'inline-flex';
        openUrlBtn.setAttribute('data-url', data);
    } else {
        openUrlBtn.style.display = 'none';
    }
    
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Open scanned URL
function openScannedURL() {
    const btn = document.getElementById('open-url-btn');
    const url = btn.getAttribute('data-url');
    if (url) {
        window.open(url, '_blank');
    }
}

// Copy scanned text
function copyScannedText() {
    const text = document.getElementById('scan-result-text').textContent;
    navigator.clipboard.writeText(text).then(() => {
        showAlert('scan', 'Text copied to clipboard!');
    }).catch(err => {
        console.error('Copy failed:', err);
        showAlert('scan', 'Failed to copy text');
    });
}

// Drag and drop for file upload
document.addEventListener('DOMContentLoaded', function() {
    const fileUploadArea = document.querySelector('.qr-file-upload');
    
    if (fileUploadArea) {
        fileUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUploadArea.classList.add('dragover');
        });
        
        fileUploadArea.addEventListener('dragleave', () => {
            fileUploadArea.classList.remove('dragover');
        });
        
        fileUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUploadArea.classList.remove('dragover');
            
            const file = e.dataTransfer.files[0];
            if (file) {
                const fileInput = document.getElementById('file-input');
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                handleFileSelect({ target: fileInput });
            }
        });
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopCamera();
});

// Enter key support for text QR generation
document.addEventListener('DOMContentLoaded', function() {
    const qrTextArea = document.getElementById('qr-text');
    if (qrTextArea) {
        qrTextArea.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                generateTextQR();
            }
        });
    }
});
