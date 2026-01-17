document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Upload page initialized');
    
    const uploadArea = document.getElementById('uploadArea');
    const videoFile = document.getElementById('videoFile');
    const uploadPreview = document.getElementById('uploadPreview');
    const uploadPlaceholder = uploadArea.querySelector('.upload-placeholder');
    const previewVideo = document.getElementById('previewVideo');
    let selectedCategories = new Set();
    let isSubmitting = false
    
    // Verify elements exist
    if (!uploadArea) console.error('❌ uploadArea not found');
    if (!videoFile) console.error('❌ videoFile not found');
    
    // Load categories
    loadCategories();
    
    // File selection
    document.getElementById('selectFileBtn').addEventListener('click', () => {
        videoFile.click();
    });
    
    document.getElementById('changeFileBtn').addEventListener('click', () => {
        videoFile.click();
    });
    
    videoFile.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleVideoFile(file);
        }
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('video/')) {
            videoFile.files = e.dataTransfer.files;
            handleVideoFile(file);
        }
    });
    
    function handleVideoFile(file) {
        const url = URL.createObjectURL(file);
        previewVideo.src = url;
        uploadPlaceholder.style.display = 'none';
        uploadPreview.style.display = 'block';
    }
    
    async function loadCategories() {
        
        try {
            const response = await fetch('/api/categories/');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            const categoriesSelect = document.getElementById('categories');
            
            if (!categoriesSelect) {
                console.error('❌ Categories select element not found in DOM!');
                return;
            }
            
            if (!data || data.length === 0) {
                categoriesSelect.innerHTML = '<option value="">No categories available - Please contact admin</option>';
                alert('No categories available. Please contact administrator to set up categories.');
                return;
            }
            
            // Clear and rebuild select
            categoriesSelect.innerHTML = '<option value="">-- Select Categories --</option>';
            
            // Group by parent category
            const parentCategories = {};
            
            data.forEach(category => {
                if (!category.parent_category) {
                    return;
                }
                
                const parentName = category.parent_category.name;
                
                if (!parentCategories[parentName]) {
                    parentCategories[parentName] = [];
                }
                
                parentCategories[parentName].push(category);
            });
            
            // Create optgroups
            Object.keys(parentCategories).sort().forEach(parentName => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = parentName;
                
                parentCategories[parentName].forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.category_id;
                    option.textContent = category.name;
                    optgroup.appendChild(option);
                });
                
                categoriesSelect.appendChild(optgroup);
            });
            
            // Add change listener
            categoriesSelect.addEventListener('change', function() {
                selectedCategories.clear();
                const selected = Array.from(this.selectedOptions);
                selected.forEach(option => {
                    if (option.value) {
                        selectedCategories.add(option.value);
                    }
                });
            });

            
        } catch (error) {
            
            const categoriesSelect = document.getElementById('categories');
            if (categoriesSelect) {
                categoriesSelect.innerHTML = '<option value="">Error loading categories</option>';
            }
            
            alert('Failed to load categories: ' + error.message + '\n\nPlease check:\n1. Django server is running\n2. Database has categories\n3. Browser console for details');
        }
    }
    
    // Form submission
    document.getElementById('uploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        if (isSubmitting){
            return;
        }
        isSubmitting = true;

        if (selectedCategories.size === 0) {
            showToast('Please select at least one category', 'error');
            return;
        }
        
        const formData = new FormData(this);
        
        // Remove the select's default submission and add our selected categories
        formData.delete('categories');
        selectedCategories.forEach(cat => {
            formData.append('categories', cat);
        });
        
        // Show progress
        document.getElementById('uploadProgress').style.display = 'block';
        document.getElementById('submitBtn').disabled = true;
        
        try {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    document.getElementById('progressFill').style.width = percent + '%';
                    document.getElementById('progressText').textContent = 
                        `Uploading... ${Math.round(percent)}%`;
                }
            });
            
            xhr.addEventListener('load', function() {

                if (xhr.status === 200 || xhr.status === 201) {
                    showToast('Video uploaded successfully!', 'success');
                    setTimeout(() => window.location.href = '/', 2000);
                } else {
                    console.error('Upload failed:', xhr.responseText);
                    try {
                        const error = JSON.parse(xhr.responseText);
                        console.error('Error details:', error);
                        showToast('Upload failed: ' + JSON.stringify(error), 'error');
                    } catch(e) {
                        showToast('Upload failed: ' + xhr.responseText, 'error');
                    }
                    document.getElementById('submitBtn').disabled = false;
                }
            });
            
            xhr.addEventListener('error', function() {
                console.error('Upload error');
                showToast('Upload failed. Please try again.', 'error');
                document.getElementById('submitBtn').disabled = false;
            });
            
            xhr.open('POST', '/api/videos/');
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
            xhr.send(formData);
            
        } catch (error) {
            console.error('Upload exception:', error);
            showToast(error.message, 'error');
            document.getElementById('submitBtn').disabled = false;
        }
    });
});

function showToast(message, type) {
    // Simple alert for now - you can make this fancier
    if (type === 'error') {
        alert('❌ ' + message);
    } else {
        alert('✅ ' + message);
    }
}