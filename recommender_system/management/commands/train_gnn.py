from django.core.management.base import BaseCommand
from recommender_system.recommendation_engine import recommendation_engine
import time

class Command(BaseCommand):
    help = 'Train the Graph Neural Network (GNN) model for recommendations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--epochs',
            type = int,
            default = 30,
            help = 'Number of training epochs (default: 30)',
        )
        parser.add_argument(
            '--hidden-dim',
            type = int,
            default = 128,
            help = 'Dimension of hidden layers (default: 128)',
        )
        parser.add_argument(
            '--force',
            action = 'store_true',
            help = 'Force retraining even if a trained model exists',
        )
        parser.add_argument(
            '--bulk-sync',
            action = 'store_true',
            help = 'Perform bulk sync of all Django data to Neo4j before training',
        )
        
    def handle(self, *args, **options):
        epochs = options['epochs']
        hidden_dim = options['hidden_dim']
        force_retrain = options['force']
        bulk_sync = options['bulk_sync']
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🚀 Starting Recommendation Model Training')
        )
        self.stdout.write(f'   Epochs: {epochs}')
        self.stdout.write(f'   Hidden Dimension: {hidden_dim}')
        self.stdout.write(f'   Bulk Sync: {bulk_sync}\n')
        
        self.stdout.write(self.style.WARNING(f'Starting GNN training for {epochs} epochs with hidden dim {hidden_dim}...'))
        
        if not force_retrain and not recommendation_engine.check_model_needs_training():
            self.stdout.write(self.style.SUCCESS('Trained model already exists. Use --force to retrain. Exiting.'))
            return
        
        start_time = time.time()
        recommendation_engine.train_gnn_and_update_embeddings(num_epochs = epochs, hidden_dim = hidden_dim)
        
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f'GNN training completed in {elapsed_time:.2f} seconds.'))
        
        if bulk_sync:
            self.stdout.write('Performing bulk sync of Django data to Neo4j...')
            recommendation_engine.bulk_sync_all_data_to_neo4j()
            self.stdout.write(self.style.SUCCESS('Bulk sync completed\n'))
            