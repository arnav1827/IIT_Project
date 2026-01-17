from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import User, Video, Watch, Like, Follow
from .recommendation_engine import recommendation_engine

@receiver(post_save, sender = User)
def sync_user_on_save(sender, instance, created, **kwargs):
    
    if created:
        recommendation_engine.sync_user_to_neo4j(instance)

@receiver(post_save, sender = Video)
def sync_video_on_save(sender, instance, created, **kwargs):
    
    if created:
        recommendation_engine.sync_video_to_neo4j(instance)

@receiver(post_save, sender = Watch)
def sync_watch_on_save(sender, instance, created, **kwargs):
    
    if created:
        recommendation_engine.sync_watch_to_neo4j(instance)

@receiver(post_save, sender = Like)
def sync_like(sender, instance, created, **kwargs):
    
    if created:
        recommendation_engine.sync_like_to_neo4j(instance)
        
@receiver(post_save, sender = Follow)
def sync_follow(sender, instance, created, **kwargs):
    
    if created:
        recommendation_engine.sync_follow_to_neo4j(instance)