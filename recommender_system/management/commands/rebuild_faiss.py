from django.core.management.base import BaseCommand
from recommender_system.recommendation_engine import recommendation_engine

class Command(BaseCommand):
    help = 'Rebuild faiss index from existing embeddings in Neo4j.'
    
    def handle(self, *args, **options):
        recommendation_engine._build_faiss_index()
        recommendation_engine._save_faiss_index()
        
        self.stdout.write(self.style.SUCCESS(f'FAISS index rebuild with {len(recommendation_engine.video_ids)} videos'))
        