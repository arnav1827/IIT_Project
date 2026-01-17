from django.core.management.base import BaseCommand
from recommender_system.recommendation_engine import recommendation_engine

class Command(BaseCommand):
    help = 'Initialize Neo4j database schema (constraints, indexes)'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Initializing Neo4j database schema...'))
        recommendation_engine.initialize_neo4j_schema()
        self.stdout.write(self.style.SUCCESS('Neo4j database schema initialized successfully.'))