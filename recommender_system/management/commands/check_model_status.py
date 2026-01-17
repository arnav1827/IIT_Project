from django.core.management.base import BaseCommand
from recommender_system import recommendation_engine
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Check status of GNN model and Neo4j database'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Checking GNN model status...'))
        
        if os.path.exists(recommendation_engine.MODEL_PATH):
            size = os.path.getsize(recommendation_engine.MODEL_PATH) / (1024 * 1024)
            mtime = os.path.getmtime(recommendation_engine.MODEL_PATH)
            modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(f'Model: {recommendation_engine.MODEL_PATH} ({size:.2f} MB)')
            self.stdout.write(f'Last Modified: {modified}')
        else:
            self.stdout.write('No trained GNN model found.')
            
        if os.path.exists(recommendation_engine.FAISS_INDEX_PATH):
            size = os.path.getsize(recommendation_engine.FAISS_INDEX_PATH) / (1024 * 1024)
            self.stdout.write(f'FAISS Index: {recommendation_engine.FAISS_INDEX_PATH} ({size:.2f} MB)')
        else:
            self.stdout.write('No FAISS index found.')
            
        needs_training = recommendation_engine.check_model_needs_training()
        
        if needs_training:
            self.stdout.write(self.style.ERROR('GNN model needs training.'))
        else:
            self.stdout.write(self.style.SUCCESS('GNN model is up-to-date.'))
            