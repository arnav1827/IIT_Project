document.addEventListener('DOMContentLoaded', function() {
    console.log('🎬 Video page loaded - Video ID:', videoId);
    
    const video = document.getElementById('mainVideo');
    let watchStartTime = Date.now();
    let hasRecordedView = false;
    
    // Track video watch
    video.addEventListener('timeupdate', function() {
        const watchPercentage = (video.currentTime / video.duration);
        
        // Record view after 30% watched
        if (watchPercentage >= 0.3 && !hasRecordedView) {
            recordWatch(watchPercentage);
            hasRecordedView = true;
        }
    });
    
    // Record watch on page leave
    window.addEventListener('beforeunload', function() {
        if (video.currentTime > 0) {
            const watchPercentage = video.currentTime / video.duration;
            recordWatch(watchPercentage);
        }
    });
    
    async function recordWatch(watchTime) {
        try {
            console.log(`📊 Recording watch - Video: ${videoId}, Time: ${watchTime.toFixed(2)}`);
            
            const response = await fetch(`/api/videos/${videoId}/watch/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ watch_time: Math.min(watchTime, 1.0) })
            });
            
            const text = await response.text();
            console.log('Watch response:', response.status, text);
            
            if (!response.ok) {
                console.error('❌ Watch recording failed:', response.status);
                return;
            }
            
            try {
                const data = JSON.parse(text);
                console.log('✅ Watch recorded:', data);
            } catch (e) {
                console.log('✅ Watch recorded (no JSON response)');
            }
        } catch (error) {
            console.error('❌ Error recording watch:', error);
        }
    }
    
    // Like button
    const likeBtn = document.getElementById('likeBtn');
    if (likeBtn) {
        likeBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('💗 Like button clicked for video:', videoId);
            
            try {
                const response = await fetch(`/api/videos/${videoId}/like/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/json'
                    }
                });
                
                console.log('Like response status:', response.status);
                
                const text = await response.text();
                console.log('Like response text:', text);
                
                if (!response.ok) {
                    console.error('❌ Like failed with status:', response.status);
                    alert('Error: ' + response.status);
                    return;
                }
                
                try {
                    const data = JSON.parse(text);
                    console.log('Like data:', data);
                    
                    if (data.likes !== undefined) {
                        document.getElementById('likeCount').textContent = data.likes;
                        likeBtn.classList.toggle('liked');
                        console.log('✅ Video liked successfully');
                    }
                } catch (e) {
                    console.error('❌ Failed to parse like response:', e);
                }
            } catch (error) {
                console.error('❌ Like error:', error);
            }
        });
    }
    
    // Follow button
    const followBtn = document.getElementById('followBtn');
    if (followBtn) {
        followBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            console.log('👥 Follow button clicked for user:', creatorId);
            
            try {
                const response = await fetch(`/api/users/${creatorId}/follow/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/json'
                    }
                });
                
                console.log('Follow response status:', response.status);
                
                const text = await response.text();
                console.log('Follow response text:', text);
                
                if (!response.ok) {
                    console.error('❌ Follow failed with status:', response.status);
                    alert('Error: ' + response.status);
                    return;
                }
                
                try {
                    const data = JSON.parse(text);
                    console.log('Follow data:', data);
                    
                    if (data.status === 'following') {
                        followBtn.innerHTML = '<i class="fas fa-check"></i> Following';
                        followBtn.classList.remove('btn-primary');
                        followBtn.classList.add('btn-outline');
                        console.log('✅ User followed successfully');
                    } else if (data.status === 'unfollowed') {
                        followBtn.innerHTML = '<i class="fas fa-user-plus"></i> Follow';
                        followBtn.classList.remove('btn-outline');
                        followBtn.classList.add('btn-primary');
                        console.log('✅ User unfollowed successfully');
                    }
                } catch (e) {
                    console.error('❌ Failed to parse follow response:', e);
                }
            } catch (error) {
                console.error('❌ Follow error:', error);
            }
        });
    }
    
    // Load recommended videos
    loadRecommendations();
    
    async function loadRecommendations() {
        try {
            const response = await fetch('/api/recommendations/?limit=10');
            
            if (!response.ok) {
                console.error('Failed to load recommendations:', response.status);
                return;
            }
            
            const text = await response.text();
            const videos = JSON.parse(text);
            
            console.log('📺 Recommended videos:', videos);
            const container = document.getElementById('recommendedVideos');
            
            if (!videos || videos.length === 0) {
                container.innerHTML = '<p>No recommendations available</p>';
                return;
            }
            
            container.innerHTML = videos.map(v => `
                <a href="/video/${v.video_id}/" class="recommended-video">
                    <img src="${v.thumbnail ? v.thumbnail : '/static/images/default-thumbnail.jpg'}" alt="${v.title}">
                    <div class="recommended-info">
                        <h4>${v.title}</h4>
                        <p>${v.creator_username}</p>
                        <p class="stats">${formatNumber(v.views)} views</p>
                    </div>
                </a>
            `).join('');
        } catch (error) {
            console.error('❌ Error loading recommendations:', error);
        }
    }
    
    function formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num;
    }
});