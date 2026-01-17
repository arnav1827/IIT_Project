from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Video, Category, ParentCategory, 
    Watch, Like, Follow, UserCategoryInterest
)

# ========== USER ADMIN ==========

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""
    
    list_display = ['username', 'email', 'verified', 'get_video_count', 'created_at']
    list_filter = ['verified', 'is_staff', 'created_at']
    search_fields = ['username', 'email', 'bio']
    readonly_fields = ['created_at', 'updated_at', 'id', 'get_video_count', 'get_follower_count', 'get_following_count']
    
    fieldsets = (
        ('Basic Info', {'fields': ('username', 'email', 'password')}),
        ('Profile', {'fields': ('bio', 'profile_picture', 'banner_image', 'website', 'location')}),
        ('Status', {'fields': ('verified', 'is_active', 'is_staff', 'is_superuser')}),
        ('Statistics', {'fields': ('get_video_count', 'get_follower_count', 'get_following_count')}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
        ('ID', {'fields': ('id',)}),
    )
    
    def get_video_count(self, obj):
        """Get video count"""
        return obj.video_count
    get_video_count.short_description = 'Videos Created'
    
    def get_follower_count(self, obj):
        """Get follower count"""
        return obj.follower_count
    get_follower_count.short_description = 'Followers'
    
    def get_following_count(self, obj):
        """Get following count"""
        return obj.following_count
    get_following_count.short_description = 'Following'


# ========== CATEGORY ADMIN ==========

@admin.register(ParentCategory)
class ParentCategoryAdmin(admin.ModelAdmin):
    """Parent category admin"""
    
    list_display = ['name', 'icon', 'get_category_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_category_count(self, obj):
        """Get count of subcategories"""
        return obj.categories.count()
    get_category_count.short_description = 'Subcategories'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin"""
    
    list_display = ['name', 'parent_category', 'get_video_count', 'created_at']
    list_filter = ['parent_category', 'created_at']
    search_fields = ['name', 'parent_category__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_video_count(self, obj):
        """Get count of videos in this category"""
        return obj.videos.count()
    get_video_count.short_description = 'Videos'


# ========== VIDEO ADMIN ==========

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Video admin"""
    
    list_display = ['title', 'creator', 'get_category_count', 'views', 'is_public', 'created_at']
    list_filter = ['is_public', 'is_premium', 'created_at', 'categories__parent_category']
    search_fields = ['title', 'description', 'creator__username']
    readonly_fields = ['created_at', 'updated_at', 'views']
    filter_horizontal = ['categories', 'parent_categories']
    
    fieldsets = (
        ('Basic Info', {'fields': ('video_id', 'title', 'description')}),
        ('Media', {'fields': ('thumbnail', 'video_file', 'duration')}),
        ('Creator', {'fields': ('creator',)}),
        ('Categories', {'fields': ('categories', 'parent_categories')}),
        ('Settings', {'fields': ('is_public', 'is_premium')}),
        ('Statistics', {'fields': ('views', 'likes')}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )
    
    def get_category_count(self, obj):
        """Get count of categories"""
        return obj.categories.count()
    get_category_count.short_description = 'Categories'


# ========== INTERACTION ADMIN ==========

@admin.register(Watch)
class WatchAdmin(admin.ModelAdmin):
    """Watch history admin"""
    
    list_display = ['user', 'video', 'watch_time', 'watched_duration', 'timestamp']
    list_filter = ['timestamp', 'watch_time']
    search_fields = ['user__username', 'video__title']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """Like admin"""
    
    list_display = ['user', 'video', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user__username', 'video__title']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Follow admin"""
    
    list_display = ['follower', 'followee', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['follower__username', 'followee__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(UserCategoryInterest)
class UserCategoryInterestAdmin(admin.ModelAdmin):
    """User category interest admin"""
    
    list_display = ['user', 'category', 'score', 'interaction_count', 'updated_at']
    list_filter = ['category__parent_category', 'updated_at']
    search_fields = ['user__username', 'category__name']
    readonly_fields = ['updated_at']
    ordering = ['-score']