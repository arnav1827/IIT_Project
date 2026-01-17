from django.apps import AppConfig


class RecommenderSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommender_system'

    def ready(self):
        
        from .recommendation_engine import recommendation_engine
        
        import recommender_system.signals