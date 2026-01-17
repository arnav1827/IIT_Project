from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import URLValidator
from django.utils.text import slugify
import uuid
from django.core.validators import FileExtensionValidator

# ========== USER MODEL ==========

class User(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='banners/', blank=True, null=True)
    website = models.URLField(blank=True, null=True, validators=[URLValidator()])
    location = models.CharField(max_length=100, blank=True, null=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix reverse accessor clashes by adding related_name
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups',  # Changed from default
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',  # Changed from default
        blank=True
    )
    
    class Meta:
        db_table = 'recommender_system_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
    
    @property
    def video_count(self):
        return self.videos.count()
    
    @property
    def follower_count(self):
        """Count followers"""
        return self.followers.count()
    
    @property
    def following_count(self):
        """Count following"""
        return self.following.count()


# ========== CATEGORY MODELS ==========

class ParentCategory(models.Model):
    """Parent/Main categories"""
    
    parent_category_id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📁')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Parent Category'
        verbose_name_plural = 'Parent Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Category(models.Model):
    """Sub-categories under parent categories"""
    
    category_id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    parent_category = models.ForeignKey(
        ParentCategory,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['parent_category', 'name']
    
    def __str__(self):
        return f"{self.parent_category.name} > {self.name}"


# ========== VIDEO MODEL ==========

class Video(models.Model):
    """Video model"""
    
    video_id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    video_file = models.FileField(upload_to='videos/', validators = [FileExtensionValidator(allowed_extensions = ['mp4', 'webm', 'mov'])])
    
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    
    categories = models.ManyToManyField(Category, related_name='videos')
    parent_categories = models.ManyToManyField(
        ParentCategory,
        related_name='videos',
        blank=True
    )
    
    duration = models.IntegerField(default=0)  # in seconds
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    
    is_public = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Video'
        verbose_name_plural = 'Videos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['-views']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def like_count(self):
        return self.likes_set.count()


# ========== INTERACTION MODELS ==========

class Watch(models.Model):
    """User watch history"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watches')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='watches')
    
    watch_time = models.FloatField(default=1.0)  # Weight for recommendation
    watched_duration = models.IntegerField(default=0)  # seconds watched
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'video')
        verbose_name = 'Watch History'
        verbose_name_plural = 'Watch Histories'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['video', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} watched {self.video.title}"


class Like(models.Model):
    """User likes"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes_set')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'video')
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['video', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} liked {self.video.title}"


class Follow(models.Model):
    """User follows another user"""
    
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    followee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'followee')
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['follower', '-timestamp']),
            models.Index(fields=['followee', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.follower.username} follows {self.followee.username}"
    
    def save(self, *args, **kwargs):
        """Prevent user from following themselves"""
        if self.follower == self.followee:
            raise ValueError("A user cannot follow themselves")
        super().save(*args, **kwargs)


# ========== USER INTEREST MODEL ==========

class UserCategoryInterest(models.Model):
    """Track user interest in categories"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='category_interests'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='user_interests'
    )
    
    score = models.FloatField(default=0.0)  # Accumulated interest score
    interaction_count = models.IntegerField(default=0)  # Number of interactions
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'category')
        verbose_name = 'User Category Interest'
        verbose_name_plural = 'User Category Interests'
        ordering = ['-score']
        indexes = [
            models.Index(fields=['user', '-score']),
        ]
    
    def __str__(self):
        return f"{self.user.username} interested in {self.category.name}"