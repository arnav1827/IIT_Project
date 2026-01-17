from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'videos', views.VideoViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'parent-categories', views.ParentCategoryViewSet)

urlpatterns = [
    path('', views.home, name = 'home'),
    path('profile/<str:username>/', views.profile, name = 'profile'),
    path('video/<str:video_id>/', views.video_detail, name = 'video_detail'),
    path('upload/', views.upload, name = 'upload'),
    path('following/', views.following_feed, name = 'following_feed'),
    path('explore/', views.explore, name = 'explore'),
    
    path('api/', include(router.urls)),
    
    path('api/categories/parent/', views.get_parent_categories, name = 'parent_categories'),
    
    path('api/recommendations/', views.get_recommendations, name = 'recommendations'),
    path('api/following-feed', views.get_following_feed, name = 'following_feed_api'),
    path('api/category-feed/<str:parent_category_id>/', views.get_category_feed, name = 'category_feed'),
    path('api/user-interests/', views.get_user_interests, name = 'user_interests'),
    
    path('api/auth/register/', views.register, name='register'),
    path('api/auth/login/', views.login_view, name='login'),
    path('api/auth/logout/', views.logout_view, name='logout'),
    path('api/auth/me/', views.current_user, name='current_user'),
]