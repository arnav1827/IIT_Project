from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from .models import User, Video, Category, ParentCategory, Watch, Like, Follow, UserCategoryInterest
from .serializers import (UserSerializer, VideoSerializer, CategorySerializer, ParentCategorySerializer,
                          WatchSerializer, LikeSerializer, FollowSerializer, UserCategoryInterestSerializer)

from .recommendation_engine import recommendation_engine
import uuid


def home(request):
    return render(request, 'home.html')

def profile(request, username):
    user = get_object_or_404(User, username = username)
    return render(request, 'profile.html', {'profile_user': user})

def video_detail(request, video_id):
    video = get_object_or_404(Video, video_id = video_id)
    return render(request, 'video.html', {'video': video})

@login_required
def upload(request):
    return render(request, 'upload.html')

@login_required
def following_feed(request):
    return render(request, 'following.html')

def explore(request):
    return render(request, 'explore.html')

# API VIEWS

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail = True, methods = ['get'])
    def videos(self, request, pk = None):
        user = self.get_object()
        videos = Video.objects.filter(creator = user).order_by('-created_at')
        serializer = VideoSerializer(videos, many = True)
        return Response(serializer.data)
    
    @action(detail = True, methods = ['get'])
    def followers(self, request, pk = None):
        user = self.get_object()
        follows = Follow.objects.filter(followee = user)
        followers = [f.follower for f in follows]
        serializer = UserSerializer(followers, many = True)
        return Response(serializer.data)
    
    @action(detail = True, methods = ['get'])
    def following(self, request, pk = None):
        user = self.get_object()
        follows = Follow.objects.filter(follower = user)
        following = [f.followee for f in follows]
        serializer = UserSerializer(following, many = True)
        return Response(serializer.data)
    
    @action(detail = True, methods = ['post'])
    def follow(self, request, pk = None):
        user_to_follow = self.get_object()
        follower = request.user
        if follower == user_to_follow:
            return Response({'error': 'Cannot follow youself'}, status = status.HTTP_400_BAD_REQUEST)
        
        follow, created = Follow.objects.get_or_create(follower = follower, followee = user_to_follow)
        
        if created:
            recommendation_engine.sync_follow_to_neo4j(follow)
            return Response({'status': 'followed'})
        else:
            return Response({'status': 'already following'})
        
    @action(detail = True, methods = ['post'])
    def unfollow(self, request, pk = None):
        user_to_unfollow = self.get_object()
        follower = request.user
        
        Follow.objects.filter(follower = follower, followee = user_to_unfollow).delete()
        
        return Response({'status': 'unfollowed'})
    
    
class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        queryset = Video.objects.all().select_related('creator')
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(categories__category_id = category)
            
        parent_category = self.request.query_params.get('parent_category', None)
        if parent_category:
            queryset = queryset.filter(parent_categories__parent_category_id = parent_category)
            
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains = search) |
                Q(description__icontains = search) |
                Q(creator__username__icontains = search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        video_id = f'video_{uuid.uuid4().hex[:12]}'
        video = serializer.save(creator = self.request.user, video_id = video_id)
        categories = self.request.data.getlist('categories')
        if categories:
            video.categories.set(categories)
            parent_ids = set()
            for cat_id in categories:
                try:
                    category = Category.objects.get(category_id=cat_id)
                    if category.parent_category:
                        parent_ids.add(category.parent_category.parent_category_id)
                except Category.DoesNotExist:
                    pass
            
            video.parent_categories.set(parent_ids)
        
        recommendation_engine.sync_video_to_neo4j(video)
        
    @action(detail = True, methods = ['post'])
    def like(self, request, pk = None):
        video = self.get_object()
        like, created = Like.objects.get_or_create(user = request.user, video = video)
        if created:
            video.likes += 1
            video.save(updated_fields = ['likes'])
            recommendation_engine.sync_like_to_neo4j(like)
            
            return Response({'status': 'liked'})
        
        else:
            return Response({'status': 'already liked'})
        
    @action(detail = True, methods = ['post'])
    def unlike(self, request, pk = None):
        video = self.get_object()
        deleted_count = Like.objects.filter(user = request.user, video = video).delete()[0]
        if deleted_count:
            video.likes = max(0, video.likes - 1)
            video.save(update_fields = ['likes'])
            
        return Response({'status': 'unliked'})
    
    @action(detail = True, methods = ['post'])
    def watch(self, request, pk = None):
        video = self.get_object()
        watch_time = float(request.data.get('watch_time', 1.0))
        watch = Watch.objects.create(user = request.user, video = video, watch_time = watch_time)
        video.views += 1
        video.save(update_fields = ['views'])
        recommendation_engine.sync_watch_to_neo4j(watch)
        
        return Response({'status': 'watched'})
    
    
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None
    
class ParentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ParentCategory.objects.all()
    serializer_class = ParentCategorySerializer
    
    
# Recommendation API Views

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendations(request):
    
    user_id = request.user.id
    limit = int(request.GET.get('limit', 20))
    video_detail = recommendation_engine.get_recommendations(user_id, limit = limit)
    videos = Video.objects.filter(video_id__in = video_detail)
    
    video_dict = {v.video_id: v for v in videos}
    ordered_videos = [video_dict[vid] for vid in video_detail if vid in video_dict]
    serializer = VideoSerializer(ordered_videos, many = True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_following_feed(request):
    
    user_id = request.user.id
    limit = int(request.GET.get('limit', 20))
    video_detail = recommendation_engine.get_recommendations_from_followed(user_id, limit = limit)
    videos = Video.objects.filter(video_id__in = video_detail)
    
    video_dict = {v.video_id: v for v in videos}
    ordered_videos = [video_dict[vid] for vid in video_detail if vid in video_dict]
    serializer = VideoSerializer(ordered_videos, many = True)
    return Response(serializer.data)

@api_view(['GET'])
def get_category_feed(request, parent_category_id):
    
    user_id = request.user.id if request.user.is_authenticated else None
    limit = int(request.GET.get('limit', 20))
    video_detail = recommendation_engine.get_recommendations_by_category(parent_category_id, user_id, limit)
    videos = Video.objects.filter(video_id__in = video_detail)
    video_dict = {v.video_id: v for v in videos}
    ordered_videos = [video_dict[vid] for vid in video_detail if vid in video_dict]
    serializer = VideoSerializer(ordered_videos, many = True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_interests(request):
    user = request.user
    interests = UserCategoryInterest.objects.filter(user = user).select_related('category', 'category__parent_category').order_by('-score')[:10]
    serializer = UserCategoryInterestSerializer(interests, many = True)
    return Response(serializer.data)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    '''Register new user'''
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username=username, email=email, password=password)
    
    if 'interests' in request.data:
        interests = request.data.get('interests')
        user.parent_category_interests.set(interests)
    
    # Sync to Neo4j
    recommendation_engine.sync_user_to_neo4j(user)
    
    # Log in
    login(request, user)
    
    serializer = UserSerializer(user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    '''Login user'''
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        login(request, user)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    else:
        return Response({'error': 'Invalid credentials'}, 
                       status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout_view(request):
    '''Logout user'''
    logout(request)
    return Response({'status': 'logged out'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    '''Get current logged in user'''
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
def get_parent_categories(request):
    categories = ParentCategory.objects.all().values('id', 'name')
    return JsonResponse(list(categories), safe = False)