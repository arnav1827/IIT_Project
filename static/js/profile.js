document.addEventListener('DOMContentLoaded', function() {
    console.log('👤 Profile loaded for user:', profileUserId);
    
    // Load user videos
    loadUserVideos();
    
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.dataset.tab;
            
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
            
            if (tab === 'liked' && document.getElementById('likedVideos').children.length === 0) {
                loadLikedVideos();
            }
        });
    });
    
    // Follow button
    const followBtn = document.getElementById('followUserBtn');
    if (followBtn) {
        followBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('👥 Following user:', profileUserId);
            
            try {
                const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                const response = await fetch(`/api/users/${profileUserId}/follow/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                console.log('Follow response:', data);
                
                if (response.ok) {
                    this.innerHTML = '<i class="fas fa-check"></i> Following';
                    this.classList.remove('btn-primary');
                    this.classList.add('btn-outline');
                    
                    const count = document.getElementById('followerCount');
                    count.textContent = parseInt(count.textContent) + 1;
                    
                    console.log('✅ Following!');
                } else {
                    console.error('❌ Follow failed:', data);
                    alert('Error: ' + (data.error || 'Failed to follow'));
                }
            } catch (error) {
                console.error('❌ Follow error:', error);
                alert('Error: ' + error.message);
            }
        });
    }
    
    async function loadUserVideos() {
        try {
            console.log('📺 Loading videos for user:', profileUserId);
            
            const response = await fetch(`/api/videos/?creator=${profileUserId}`);
            const videos = await response.json();
            
            console.log('Videos loaded:', videos.length, videos);
            
            const container = document.getElementById('userVideos');
            
            if (!videos || videos.length === 0) {
                container.innerHTML = '<p class="empty-state">No videos yet</p>';
                return;
            }
            
            container.innerHTML = videos.map(video => createVideoCard(video)).join('');
            addVideoClickHandlers();
        } catch (error) {
            console.error('❌ Error loading videos:', error);
            document.getElementById('userVideos').innerHTML = '<p class="empty-state">Error loading videos</p>';
        }
    }
    
    async function loadLikedVideos() {
        try {
            console.log('❤️ Loading liked videos for user:', profileUserId);
            
            const response = await fetch(`/api/users/${profileUserId}/liked-videos/`);
            
            if (!response.ok) {
                document.getElementById('likedVideos').innerHTML = '<p class="empty-state">Liked videos feature coming soon</p>';
                return;
            }
            
            const videos = await response.json();
            console.log('Liked videos loaded:', videos.length);
            
            const container = document.getElementById('likedVideos');
            
            if (!videos || videos.length === 0) {
                container.innerHTML = '<p class="empty-state">No liked videos yet</p>';
                return;
            }
            
            container.innerHTML = videos.map(video => createVideoCard(video)).join('');
            addVideoClickHandlers();
        } catch (error) {
            console.error('❌ Error loading liked videos:', error);
            document.getElementById('likedVideos').innerHTML = '<p class="empty-state">Error loading liked videos</p>';
        }
    }
    
    function createVideoCard(video) {
        const thumbnail = video.thumbnail ? video.thumbnail : '/static/images/default-thumbnail.jpg';
        const views = formatNumber(video.views || 0);
        const likes = formatNumber(video.likes || 0);
        const duration = video.duration ? formatDuration(video.duration) : '0:00';
        
        return `
            <div class="video-card" data-video-id="${video.video_id}">
                <div class="video-thumbnail">
                    <img src="${thumbnail}" alt="${video.title}" onerror="this.src='/static/images/default-thumbnail.jpg'">
                    <div class="video-duration">${duration}</div>
                </div>
                <div class="video-info">
                    <div class="video-details">
                        <h3 class="video-title">${video.title}</h3>
                        <div class="video-stats">
                            <span><i class="fas fa-eye"></i> ${views} views</span>
                            <span><i class="fas fa-heart"></i> ${likes} likes</span>
                        </div>
                        <small class="upload-date">${formatDate(video.created_at)}</small>
                    </div>
                </div>
            </div>
        `;
    }
    
    function addVideoClickHandlers() {
        document.querySelectorAll('.video-card').forEach(card => {
            card.addEventListener('click', function() {
                const videoId = this.dataset.videoId;
                console.log('🎬 Opening video:', videoId);
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
    
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }
});