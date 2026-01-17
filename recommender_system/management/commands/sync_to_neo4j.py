from django.core.management.base import BaseCommand
from recommender_system.recommendation_engine import recommendation_engine
from django.db import connection
from recommender_system.models import User, Video, Category, ParentCategory, Watch, Like, Follow

class Command(BaseCommand):
    help = 'Synv data from Django to Neo4j database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--categories-only',
            action = 'store_true',
            help = 'Sync only categories',
        )
        parser.add_argument(
            '--compute-similarities',
            action = 'store_true',
            help = 'Compute video similarities',
        )
        
    def handle(self, *args, **options):
        if options['categories_only']:
            self.stdout.write(self.style.WARNING('Syncing categories to Neo4j...'))
            recommendation_engine.sync_categories_to_neo4j()
            self.stdout.write(self.style.SUCCESS('Categories synced successfully.'))
            return
        
        if options['compute_similarities']:
            self.stdout.write(self.style.WARNING('Computing video similarities...'))
            recommendation_engine.compute_video_similarities()
            self.stdout.write(self.style.SUCCESS('Video similarities computed successfully.'))
            return
        
        self.stdout.write(self.style.WARNING('Syncing data to Neo4j...'))
        recommendation_engine.bulk_sync_all_data_to_neo4j()
        self.stdout.write(self.style.SUCCESS('Data synced to Neo4j successfully.'))