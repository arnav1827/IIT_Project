from rest_framework import serializers
from .models import (User, Video, ParentCategory, Category, Watch, Like, Follow, UserCategoryInterest)


class UserSerializer(serializers.ModelSerializer):
    video_count = serializers.SerializerMethodField()
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'bio', 'profile_picture', 'follower_count', 'following_count', 'video_count', 'created_at']
        read_only_fields = ['follower_count', 'following_count', 'video_count']
        
    def get_video_count(self, obj):
        return obj.videos.count()
    
    def get_follower_count(self, obj):
        from .models import Follow
        return Follow.objects.filter(followee = obj).count()
    
    def get_following_count(self, obj):
        from .models import Follow
        return Follow.objects.filter(follower = obj).count()
        
        
class ParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentCategory
        fields = '__all__'
        
        
class CategorySerializer(serializers.ModelSerializer):
    parent_category = ParentCategorySerializer(read_only = True)
    class Meta:
        model = Category
        fields = ['category_id', 'name', 'parent_category']
        
        
class VideoSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source = 'creator.username', read_only = True)
    creator_profile_picture = serializers.ImageField(source = 'creator.profile_picture', read_only = True)
    categories_data = CategorySerializer(source = 'categories', many = True, read_only = True)
    categories = serializers.PrimaryKeyRelatedField(
        queryset = Category.objects.all(),
        many = True,
        write_only = True,
        required = False
    )
    class Meta:
        model = Video
        fields = ['video_id', 'title', 'description', 'thumbnail', 'video_file', 
                  'creator', 'creator_username', 'creator_profile_picture', 
                  'categories', 'categories_data', 'duration', 'views', 'likes', 
                  'is_public', 'is_premium', 'created_at', 'updated_at']
        read_only_fields = ['video_id', 'views', 'likes', 'creator', 'creator_username', 'creator_profile_picture']
        

class WatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watch
        fields = '__all__'
        
        
class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'
        

class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = '__all__'
        

class UserCategoryInterestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source = 'category.name', read_only = True)
    parent_category_name = serializers.CharField(source = 'category.parent_category.name', read_only = True)
    
    class Meta:
        model = UserCategoryInterest
        fields = ['id', 'user', 'category', 'category_name', 'parent_category_name', 'interaction_count', 'last_updated']
        read_only_fields = ['score', 'interaction_count', 'last_updated']