import os
import sys
import django

# Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from recommender_system.recommendation_engine import recommendation_engine
from recommender_system.models import ParentCategory, Category
from django.contrib.auth import get_user_model

User = get_user_model()

def setup_initial_categories():
    categories = {
        'entertainment': {
            'name': 'Entertainment',
            'icon': '🎬',
            'children': ['Movies', 'Music', 'Gaming', 'Comedy', 'Animation']
        },
        'education': {
            'name': 'Education',
            'icon': '📚',
            'children': ['Science', 'History', 'Math', 'Languages', 'Tutorials']
        },
        'technology': {
            'name': 'Technology',
            'icon': '💻',
            'children': ['Programming', 'AI & ML', 'Hardware', 'Reviews', 'Tech News']
        },
        'lifestyle': {
            'name': 'Lifestyle',
            'icon': '✨',
            'children': ['Fitness', 'Cooking', 'Travel', 'Fashion', 'DIY']
        },
        'news': {
            'name': 'News & Politics',
            'icon': '📰',
            'children': ['World News', 'Politics', 'Business', 'Sports', 'Weather']
        }
    }
    
    for parent_id, data in categories.items():
        parent, created = ParentCategory.objects.get_or_create(
            parent_category_id = parent_id,
            defaults = {
                'name': data['name'],
                'icon': data['icon']
            }
        )
        
        if created:
            print("Created")
            
        for child_name in data['children']:
            child_id = f'{parent_id}_{child_name.lower().replace(' ', '_').replace('&', 'and')}'
            category, created = Category.objects.get_or_create(
                category_id = child_id,
                defaults = {
                    'name': child_name,
                    'parent_category': parent
                }
            )
            
            if created:
                print("Created")
                

def create_superuser():
    if not User.objects.filter(username = 'admin').exists():
        User.objects.create_superuser(
            username = 'admin',
            email = 'mittalarnav17@gmail.com',
            password = 'Admin@123'
        )
        print('Superuser Created')
    else:
        print('Admin exists')
        
        
def main():
    setup_initial_categories()
    create_superuser()
    
    recommendation_engine.initialize_neo4j_schema()
    
    recommendation_engine.sync_categories_to_neo4j()
    
if __name__ == '__main__':
    main()