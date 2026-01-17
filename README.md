# Video Recommendation System

A Django-based video streaming platform with an intelligent recommendation engine that suggests content based on user interests and viewing behavior implementing Graph Based Semi-Supervised Learning Recommendation Algorithm

Technologies: Django, Neo4j, PyTorch Geometric, FAISS
Domain: Machine Learning, Graph Neural Networks, and Recommendation Systems

## Features

### User Management
- User registration with parent category interest selection
- User authentication (login/logout)
- Customizable user profiles with bio, profile picture, and banner
- Follow/Unfollow other creators
- User interest preferences for personalized recommendations

### Video Management
- Video upload with multiple category tagging
- Video metadata (title, description, thumbnail, duration)
- Video deletion and editing

### Interaction Tracking
- Watch history tracking (records watch time %)
- Like/Unlike videos
- View count tracking
- Engagement metrics

### Recommendation System
- **Parent Category-Based Recommendations**: Users select parent categories during registration
- **Smart Filtering**: Recommendations filtered by user's selected parent categories
- **View-Based Learning**: Tracks watch percentage to understand user preferences
- **Like-Based Signals**: Likes contribute to user interest scoring
- **Similarity Filtering**: Recommendations based on embedding similarity user behavior

### Feed Features
- Home feed with all recommendations
- Following feed (videos from followed creators)
- Category-specific feeds
- Pagination support (load more functionality in a grid format)

## System Architecture

```
IIT_Project/
├── recommender_system/          
│   ├── models.py               
│   ├── views.py                
│   ├── urls.py                 
│   ├── serializers.py          
│   ├── admin.py                
│   └── recommendation_engine.py
│
├── static/
│   ├── js/
│   │   ├── home.js            
│   │   ├── video.js           
│   │   ├── auth.js            
│   │   └── profile.js
|   |   └── app.js   
│   ├── css/
│   └── images/
│
├── templates/
│   ├── base.html              
│   ├── home.html              
│   ├── video.html             
│   ├── profile.html
|   ├── explore.html           
│   └── upload.html            
│           
│
├── setup_script.py
└── manage.py
```

### Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd IIT_Project
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create .env file**
```
NEO4J_URI = ""
NEO4J_USER = ""
NEO4J_PASSWORD = ""

DB_NAME = ""
DB_USER = ""
DB_PASSWORD = ""
DB_HOST = ""
DB_PORT = ""
```

5. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Run development server**
```bash
python setup_script.py
python manage.py runserver
```

7. **Rebuild Model and Faiss Embeddings**
```bash
python check_model_status.py
python rebuil_faiss.py
```

## Database Models

### User Model
```
- username (unique)
- email (unique)
- password (hashed)
- bio
- profile_picture
- banner_image
- website
- location
- verified (boolean)
- created_at
- updated_at
- parent_category_interests (M2M with ParentCategory)
```

### ParentCategory Model
```
- name
- icon
- description
- created_at
- updated_at
```

### Category Model
```
- name
- parent_category (FK)
- description
- icon
- created_at
- updated_at
```

### Video Model
```
- video_id (unique)
- title
- description
- creator (FK to User)
- thumbnail
- video_file (video URL)
- duration (seconds)
- categories (M2M)
- parent_categories (M2M)
- views (count)
- likes (count)
- is_public
- is_premium
- created_at
- updated_at
```

### Interaction Models

**Watch**
```
- user (FK)
- video (FK)
- watch_time (0-1 float, percentage)
- watched_duration (seconds)
- timestamp
```

**Like**
```
- user (FK)
- video (FK)
- timestamp
```

**Follow**
```
- follower (FK to User)
- followee (FK to User)
- timestamp
```

**UserCategoryInterest**
```
- user (FK)
- category (FK)
- score (float)
- interaction_count (int)
- updated_at
```

## Frontend Components

### Pages

#### Home (`/`)
- Display recommended videos based on user interests
- Category filter chips
- Video grid with pagination
- Load more functionality

#### Video Detail (`/video/{video_id}/`)
- Video player
- Like button with counter
- Creator info and follow button
- Comments section
- Recommended videos sidebar
- Watch tracking

#### Profile (`/profile/{username}/`)
- User info and stats
- **User interests display** (parent categories)
- Creator's videos
- Follower/Following counts
- Edit profile (if own profile)

#### Upload (`/upload/`)
- Video file upload
- Title and description
- Category selection (parent categories)
- Thumbnail upload
- Privacy settings

#### Authentication
- Registration modal with parent category selection
- Login form
- Logout functionality

## Recommendation Engine

### Algorithm

1. **Parent Category Filtering**
   - Filter videos by user's selected parent categories
   - Ensures relevant recommendations

2. **Watch History Analysis**
   - Videos watched >30% increase interest score
   - Higher watch % = higher interest signal

3. **Like Signals**
   - Liked videos boost category interest
   - Builds user preference profile

4. **Scoring System**
   ```
   Score = (watch_time × 0.6) + (likes × 0.4)
   ```

5. **Ranking & Filtering**
   - Videos ranked by engagement score
   - Avoid duplicates and already watched videos
   - Return top N recommendations

## Usage Guide

### User Registration with Interests
1. Click "Sign Up"
2. Enter username, email, password
3. Select parent categories** (e.g., Music, Sports, Gaming)
4. Click Register
5. Get personalized recommendations immediately

### Watching Videos
1. Click any video to play
2. Watch tracking starts automatically
3. After 30% watched → view is recorded
4. Like button available during playback
5. Recommendations update based on watch history

### Following Creators
1. Visit creator's profile
2. Click "Follow" button
3. Videos appear in your "Following" feed

### Updating Interests
1. Go to your profile
2. Click "Edit Profile"
3. Update parent category preferences
4. Save changes
5. Recommendations refresh
