document.addEventListener('DOMContentLoaded', function() {
    let currentCategory = 'all';
    let currentPage = 1;
    
    // Load initial videos
    loadVideos();
    
    // Category filter
    document.querySelectorAll('.category-chip').forEach(chip => {
        chip.addEventListener('click', function() {
            document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.dataset.category;
            currentPage = 1;
            loadVideos(true);
        });
    });
    
    // Load more
    document.getElementById('loadMoreBtn').addEventListener('click', function() {
        currentPage++;
        loadVideos();
    });
    
    async function loadVideos(replace = true) {
        const grid = document.getElementById('videoGrid');
        
        if (replace) {
            grid.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></div>';
        }
        
        try {
            let url;
            if (currentCategory === 'all') {
                url = '/api/recommendations/?limit=20';
            } else {
                url = `/api/category-feed/${currentCategory}/?limit=20`;
            }
            
            const response = await fetch(url);
            const videos = await response.json();
            
            if (replace) {
                grid.innerHTML = '';
            } else {
                grid.querySelector('.loading-spinner')?.remove();
            }
            
            videos.forEach(video => {
                const videoCard = createVideoCard(video);
                grid.insertAdjacentHTML('beforeend', videoCard);
            });
            
            // Add click handlers
            addVideoClickHandlers();
            
        } catch (error) {
            console.error('Error loading videos:', error);
            grid.innerHTML = '<div class="error-message">Failed to load videos. Please try again.</div>';
        }
    }
    
    function createVideoCard(video) {
        return `
            <div class="video-card" data-video-id="${video.video_id}">
                <div class="video-thumbnail">
                    <img src="${video.thumbnail || '/static/images/default-thumbnail.jpg'}" 
                         alt="${video.title}">
                    <div class="video-duration">${formatDuration(video.duration)}</div>
                    <div class="video-overlay">
                        <i class="fas fa-play-circle"></i>
                    </div>
                </div>
                <div class="video-info">
                    <img src="${video.creator_profile_picture || '/static/images/default-avatar.png'}" 
                         alt="${video.creator_username}" 
                         class="creator-avatar">
                    <div class="video-details">
                        <h3 class="video-title">${video.title}</h3>
                        <p class="creator-name">${video.creator_username}</p>
                        <div class="video-stats">
                            <span><i class="fas fa-eye"></i> ${formatNumber(video.view_count)}</span>
                            <span><i class="fas fa-heart"></i> ${formatNumber(video.like_count)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    function addVideoClickHandlers() {
        document.querySelectorAll('.video-card').forEach(card => {
            card.addEventListener('click', function() {
                const videoId = this.dataset.videoId;
                window.location.href = `/video/${videoId}/`;
            });
        });
    }
    
    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    function formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num;
    }
});