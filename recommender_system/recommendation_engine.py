from neo4j import GraphDatabase
from django.conf import settings
import numpy as np
import os
import pickle
import faiss
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import GCNConv
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from recommender_system.models import User, Video, Category, ParentCategory, Watch, Like, Follow, UserCategoryInterest
from django.utils import timezone

# GNN MODEL

class HeteroGNNModel(nn.Module):
    """Heterogeneous GNN for recommendation embeddings"""
    
    def __init__(self, hidden_dim = 128, num_layers = 3):
        super().__init__()
        self.hidden_dim = hidden_dim
        
        self.input_projs = nn.ModuleDict({
            'user': nn.Linear(64, hidden_dim),
            'video': nn.Linear(64, hidden_dim),
            'category': nn.Linear(64, hidden_dim),
            'parent_category': nn.Linear(64, hidden_dim)
        })
        
        self.convs = nn.ModuleList([
            GCNConv(hidden_dim, hidden_dim) for _ in range(num_layers)
        ])
        self.norms = nn.ModuleList([
            nn.LayerNorm(hidden_dim) for _ in range(num_layers)
        ])
        self.dropout = nn.Dropout(0.3)
    
    def forward(self, x_dict, edge_index_dict):
        for node_type in x_dict.keys():
            x_dict[node_type] = self.input_projs[node_type](x_dict[node_type])
        
        for i, conv in enumerate(self.convs):
            x_dict_new = {}
            
            for edge_type in edge_index_dict.keys():
                src_type, _, dst_type = edge_type
                edge_index = edge_index_dict[edge_type]
                
                if src_type == dst_type:
                    x = conv(x_dict[src_type], edge_index)
                    x = self.norms[i](x)
                    x = F.relu(x)
                    x = self.dropout(x)
                    
                    if dst_type not in x_dict_new:
                        x_dict_new[dst_type] = x
                    else:
                        x_dict_new[dst_type] += x
            
            for node_type in x_dict_new:
                x_dict[node_type] = x_dict[node_type] + x_dict_new[node_type]
        
        return x_dict


# RECOMMENDATION ENGINE WITH TRAINING

class RecommendationEngine:
    
    MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
    MODEL_PATH = os.path.join(MODEL_DIR, 'gnn_model.pt')
    METADATA_PATH = os.path.join(MODEL_DIR, 'model_metadata.pkl')
    FAISS_INDEX_PATH = os.path.join(MODEL_DIR, 'faiss_index.bin')
    VIDEO_IDS_PATH = os.path.join(MODEL_DIR, 'video_ids.pkl')
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        
        os.makedirs(self.MODEL_DIR, exist_ok = True)
        
        self.model = None
        self.node_mappings = {}
        self.reverse_mappings = {}
        self.data = None
        self.model_metadata = {}
        
        self.faiss_index = None
        self.video_ids = []
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self._load_model_if_exists()
        self._load_faiss_index_if_exists()
    
    def close(self):
        self.driver.close()
        
    def initialize_neo4j_schema(self):
        
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
                "CREATE CONSTRAINT video_id IF NOT EXISTS FOR (v:Video) REQUIRE v.video_id IS UNIQUE",
                "CREATE CONSTRAINT category_id IF NOT EXISTS FOR (c:Category) REQUIRE c.category_id IS UNIQUE",
                "CREATE CONSTRAINT parent_category_id IF NOT EXISTS FOR (pc:ParentCategory) REQUIRE pc.parent_category_id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation failed: {e}")
                    
            indexes = [
                "CREATE INDEX user_username IF NOT EXISTS FOR (u:User) ON (u.username)",
                "CREATE INDEX video_categories IF NOT EXISTS FOR (v:Video) ON (v.categories)",
                "CREATE INDEX video_parent_categories IF NOT EXISTS FOR (v:Video) ON (v.parent_categories)",
                "CREATE INDEX category_name IF NOT EXISTS FOR (c:Category) ON (c.name)",
                "CREATE INDEX watches_timestamp IF NOT EXISTS FOR ()-[r:WATCHES]-() ON (r.timestamp)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"Index creation failed: {e}")
                    
    def sync_categories_to_neo4j(self):
        
        with self.driver.session() as session:
            for parent_cat in ParentCategory.objects.all():
                session.run('''
                MERGE (pc:ParentCategory {parent_category_id: $parent_category_id})
                SET pc.name = $name,
                    pc.updated_at = datetime()
                ''',
                parent_category_id = parent_cat.parent_category_id,
                name = parent_cat.name)
                
            for category in Category.objects.select_related('parent_category').all():
                session.run('''
                            MERGE (c:Category {category_id: $category_id})
                            SET c.name = $name,
                                c.parent_category = $parent_category_id,
                                c.updated_at = datetime()
                                
                            MERGE (pc:ParentCategory {parent_category_id: $parent_category_id})
                            MERGE (c)-[:PARENT_OF]->(pc)
                            ''',
                            category_id = category.category_id,
                            name = category.name,
                            parent_category_id = category.parent_category.parent_category_id)
                
    def bulk_sync_all_data_to_neo4j(self):
        
        self.sync_categories_to_neo4j()
        
        for user in User.objects.all():
            self.sync_user_to_neo4j(user)
            
        for video in Video.objects.select_related('creator').prefetch_related('categories', 'parent_categories').all():
            self.sync_video_to_neo4j(video)
            
        watch_count = 0
        for watch in Watch.objects.select_related('user', 'video').all()[:10000]:
            self.sync_watch_to_neo4j(watch)
            watch_count += 1
            if watch_count % 1000 == 0:
                print(f"  ✓ Synced {watch_count} watches")
                
        for like in Like.objects.select_related('user', 'video').all():
            self.sync_like_to_neo4j(like)
            # changed following to followee in the below line
        for follow in Follow.objects.select_related('follower', 'followee').all():
            self.sync_follow_to_neo4j(follow)
            
        self.compute_video_similarities()

    def compute_video_similarities(self):
        
        with self.driver.session() as session:
            query = '''
            MATCH (v1:Video), (v2:Video)
            WHERE v1.video_id < v2.video_id
              AND v1.categories IS NOT NULL
              AND v2.categories IS NOT NULL
            
            WITH v1, v2,
                 toFloat(size([c IN v1.categories WHERE c IN v2.categories])) /
                 size(v1.categories + [c IN v2.categories WHERE NOT c IN v1.categories]) as cat_sim
            
            WHERE cat_sim >= 0.3
            
            MERGE (v1)-[s:SIMILAR_TO]-(v2)
            SET s.similarity = cat_sim,
                s.updated_at = datetime()
            
            RETURN count(s) as count
        '''

            result = session.run(query)
            count = result.single()['count']
            
    def _load_model_if_exists(self):
        
        if os.path.exists(self.MODEL_PATH) and os.path.exists(self.METADATA_PATH):
            try:
                with open(self.METADATA_PATH, 'rb') as f:
                    self.model_metadata = pickle.load(f)
                    
                hidden_dim = self.model_metadata.get('hidden_dim', 128)
                self.model = HeteroGNNModel(hidden_dim = hidden_dim).to(self.device)
                self.model.load_state_dict(torch.load(self.MODEL_PATH, map_location = self.device))
                self.model.eval()
                
                self.node_mappings = self.model_metadata.get('node_mappings', {})
                self.reverse_mappings = self.model_metadata.get('reverse_mappings', {})
                
            except Exception as e:
                self.model = None
                
    def _save_model(self):
        torch.save(self.model.state_dict(), self.MODEL_PATH)
        self.model_metadata = {
            'hidden_dim': self.model.hidden_dim,
            'node_mappings': self.node_mappings,
            'reverse_mappings': self.reverse_mappings,
            'last_trained': datetime.now().isoformat(),
            'total_epochs': self.model_metadata.get('total_epochs', 0) + 30,
        }
        
    def _load_faiss_index_if_exists(self):
        if os.path.exists(self.FAISS_INDEX_PATH) and os.path.exists(self.VIDEO_IDS_PATH):
            try:
                self.faiss_index = faiss.read_index(self.FAISS_INDEX_PATH)
                
                with open(self.VIDEO_IDS_PATH, 'rb') as f:
                    self.video_ids = pickle.load(f)
                    
            except Exception as e:
                self.faiss_index = None
                
    def _save_faiss_index(self):
        if self.faiss_index is not None:
            faiss.write_index(self.faiss_index, self.FAISS_INDEX_PATH)
            with open(self.VIDEO_IDS_PATH, 'wb') as f:
                pickle.dump(self.video_ids, f)
                
    def check_model_needs_training(self) -> bool:
        
        if self.model is None:
            return True
        
        last_trained = self.model_metadata.get('last_trained')
        if last_trained:
            last_trained_dt = datetime.fromisoformat(last_trained)
            
            if timezone.is_aware(last_trained_dt):
                now = timezone.now()
            else:
                now = datetime.now()
            
            if (now - last_trained_dt) > timedelta(days = 7):
                return True
            
        with self.driver.session() as session:
            result = session.run("MATCH (u:User) RETURN count(u) as count")
            current_users = result.single()['count']
            
            result = session.run("MATCH (v:Video) RETURN count(v) as count")
            current_videos = result.single()['count']
            
            trained_users = len(self.node_mappings.get('user', {}))
            trained_videos = len(self.node_mappings.get('video', {}))
            
            if current_users > trained_users * 1.2 or current_videos > trained_videos * 1.2:
                return True
            
        return False

    def sync_user_to_neo4j(self, user):
        
        with self.driver.session() as session:
            session.run('''
                MERGE (u:User {user_id: $user_id})
                SET u.username = $username,
                    u.updated_at = datetime()
            ''', user_id = str(user.id), username = user.username)
    
    def sync_video_to_neo4j(self, video):
        
        with self.driver.session() as session:
            category_ids = [c.category_id for c in video.categories.all()]
            parent_category_ids = [pc.parent_category_id for pc in video.parent_categories.all()]
            
            session.run('''
                MERGE (v:Video {video_id: $video_id})
                SET v.title = $title,
                    v.categories = $categories,
                    v.parent_categories = $parent_categories,
                    v.updated_at = datetime()
                
                MERGE (creator:User {user_id: $creator_id})
                MERGE (v)-[:CREATED_BY]->(creator)
                
                WITH v
                UNWIND $categories as cat_id
                MERGE (c:Category {category_id: cat_id})
                MERGE (v)-[:BELONGS_TO]->(c)
            ''',
            video_id = video.video_id,
            title = video.title,
            categories = category_ids,
            parent_categories = parent_category_ids,
            creator_id = str(video.creator.id))
    
    def sync_watch_to_neo4j(self, watch):
        
        with self.driver.session() as session:
            session.run('''
                MATCH (u:User {user_id: $user_id})
                MATCH (v:Video {video_id: $video_id})
                
                MERGE (u)-[w:WATCHES]->(v)
                SET w.watch_time = $watch_time,
                    w.timestamp = $timestamp
                
                WITH u, v
                UNWIND v.categories as cat_id
                MATCH (c:Category {category_id: cat_id})
                MERGE (u)-[i:INTERESTED_IN]->(c)
                ON CREATE SET i.score = $watch_time, i.count = 1
                ON MATCH SET i.score = i.score + $watch_time, 
                            i.count = i.count + 1
            ''',
            user_id = str(watch.user.id),
            video_id = watch.video.video_id,
            watch_time = watch.watch_time,
            timestamp = watch.timestamp.isoformat())
        
        for category in watch.video.categories.all():
            interest, created = UserCategoryInterest.objects.get_or_create(
                user = watch.user,
                category = category
            )
            interest.score += watch.watch_time
            interest.interaction_count += 1
            interest.save()
    
    def sync_like_to_neo4j(self, like):
        
        with self.driver.session() as session:
            session.run('''
                MATCH (u:User {user_id: $user_id})
                MATCH (v:Video {video_id: $video_id})
                
                MERGE (u)-[l:LIKES]->(v)
                SET l.timestamp = $timestamp
                
                WITH u, v
                UNWIND v.categories as cat_id
                MATCH (c:Category {category_id: cat_id})
                MERGE (u)-[i:INTERESTED_IN]->(c)
                ON CREATE SET i.score = 2.0, i.count = 1
                ON MATCH SET i.score = i.score + 2.0, i.count = i.count + 1
            ''',
            user_id = str(like.user.id),
            video_id = like.video.video_id,
            timestamp = like.timestamp.isoformat())

        for category in like.video.categories.all():
            interest, created = UserCategoryInterest.objects.get_or_create(
                user = like.user,
                category = category
            )
            interest.score += 2.0
            interest.interaction_count += 1
            interest.save()
    
    # following issue (following needs to be followee)
    def sync_follow_to_neo4j(self, follow):

        with self.driver.session() as session:
            session.run('''
                MATCH (u1:User {user_id: $follower_id})
                MATCH (u2:User {user_id: $followee_id})
                
                MERGE (u1)-[f:FOLLOWS]->(u2)
                SET f.timestamp = $timestamp
            ''',
            follower_id = str(follow.follower.id),
            followee_id = str(follow.followee.id),
            timestamp = follow.timestamp.isoformat())
    
    def load_graph_from_neo4j(self) -> HeteroData:        
        data = HeteroData()
        
        nodes = self._get_all_nodes()

        for node_type, node_ids in nodes.items():
            self.node_mappings[node_type] = {nid: idx for idx, nid in enumerate(node_ids)}
            self.reverse_mappings[node_type] = {idx: nid for nid, idx in self.node_mappings[node_type].items()}
            
            num_nodes = len(node_ids)
            data[node_type].x = torch.randn(num_nodes, 64)
            data[node_type].num_nodes = num_nodes

        edges = self._get_all_edges()

        for edge_type, edge_list in edges.items():
            if len(edge_list) == 0:
                continue
            
            src_type, rel_type, dst_type = edge_type
            
            edge_index = []
            edge_attr = []
            
            for src_id, dst_id, weight in edge_list:
                if (src_id in self.node_mappings[src_type] and 
                    dst_id in self.node_mappings[dst_type]):
                    
                    src_idx = self.node_mappings[src_type][src_id]
                    dst_idx = self.node_mappings[dst_type][dst_id]
                    
                    edge_index.append([src_idx, dst_idx])
                    edge_attr.append(weight)
            
            if edge_index:
                data[edge_type].edge_index = torch.tensor(edge_index, dtype=torch.long).t()
                data[edge_type].edge_attr = torch.tensor(edge_attr, dtype=torch.float).unsqueeze(1)
        
        self.data = data
        return data
    
    def _get_all_nodes(self) -> Dict[str, List[str]]:
        with self.driver.session() as session:
            nodes = {}
            
            result = session.run("MATCH (u:User) RETURN u.user_id as id")
            nodes['user'] = [r['id'] for r in result]
            result = session.run("MATCH (v:Video) RETURN v.video_id as id")
            nodes['video'] = [r['id'] for r in result]
            result = session.run("MATCH (c:Category) RETURN c.category_id as id")
            nodes['category'] = [r['id'] for r in result]
            result = session.run("MATCH (pc:ParentCategory) RETURN pc.parent_category_id as id")
            nodes['parent_category'] = [r['id'] for r in result]
            
            return nodes
    
    def _get_all_edges(self) -> Dict[Tuple[str, str, str], List[Tuple]]:
        with self.driver.session() as session:
            edges = {}
            
            result = session.run("""
                MATCH (u:User)-[r:WATCHES]->(v:Video)
                RETURN u.user_id, v.video_id, r.watch_time
            """)
            edges[('user', 'watches', 'video')] = [
                (r['u.user_id'], r['v.video_id'], r['r.watch_time'] or 1.0) for r in result
            ]

            result = session.run("""
                MATCH (u:User)-[r:LIKES]->(v:Video)
                RETURN u.user_id, v.video_id
            """)
            edges[('user', 'likes', 'video')] = [
                (r['u.user_id'], r['v.video_id'], 1.0) for r in result
            ]

            result = session.run("""
                MATCH (v:Video)-[r:BELONGS_TO]->(c:Category)
                RETURN v.video_id, c.category_id
            """)
            edges[('video', 'belongs_to', 'category')] = [
                (r['v.video_id'], r['c.category_id'], 1.0) for r in result
            ]

            result = session.run("""
                MATCH (v:Video)-[r:CREATED_BY]->(u:User)
                RETURN v.video_id, u.user_id
            """)
            edges[('video', 'created_by', 'user')] = [
                (r['v.video_id'], r['u.user_id'], 1.0) for r in result
            ]

            result = session.run("""
                MATCH (u1:User)-[r:FOLLOWS]->(u2:User)
                RETURN u1.user_id, u2.user_id
            """)
            edges[('user', 'follows', 'user')] = [
                (r['u1.user_id'], r['u2.user_id'], 1.0) for r in result
            ]

            result = session.run("""
                MATCH (u:User)-[r:INTERESTED_IN]->(c:Category)
                RETURN u.user_id, c.category_id, r.score
            """)
            edges[('user', 'interested_in', 'category')] = [
                (r['u.user_id'], r['c.category_id'], min(r['r.score'] / 10.0, 1.0))
                for r in result
            ]

            result = session.run("""
                MATCH (v1:Video)-[r:SIMILAR_TO]-(v2:Video)
                WHERE v1.video_id < v2.video_id
                RETURN v1.video_id, v2.video_id, r.similarity
            """)
            edges[('video', 'similar_to', 'video')] = [
                (r['v1.video_id'], r['v2.video_id'], r['r.similarity']) for r in result
            ]

            result = session.run("""
                MATCH (c:Category)-[r:PARENT_OF]->(pc:ParentCategory)
                RETURN c.category_id, pc.parent_category_id
            """)
            edges[('category', 'parent_of', 'parent_category')] = [
                (r['c.category_id'], r['pc.parent_category_id'], 1.0) for r in result
            ]
            
            return edges

    # GNN TRAINING
    
    def ensure_model_trained(self, force_retrain = False):
        if force_retrain or self.check_model_needs_training():
            self.train_gnn_and_update_embeddings(num_epochs = 30)
        else:
            if self.faiss_index is None:
                self._build_faiss_index()
    
    def train_gnn_and_update_embeddings(self, num_epochs = 30, hidden_dim = 128):
        
        if self.data is None:
            self.load_graph_from_neo4j()
        
        if self.model is None:
            self.model = HeteroGNNModel(hidden_dim=hidden_dim).to(self.device)
            
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)

        self.data = self.data.to(self.device)

        self.model.train()
        for epoch in range(num_epochs):
            loss = self._train_epoch(optimizer)
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss:.4f}")

        self._extract_and_store_embeddings()
        self._save_model()
        self._save_faiss_index()
    
    def _train_epoch(self, optimizer):
        total_loss = 0
        num_batches = 0

        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User)-[w:WATCHES]->(v:Video)
                RETURN u.user_id, v.video_id
                LIMIT 5000
            """)
            interactions = [(r['u.user_id'], r['v.video_id']) for r in result]
        
        if not interactions:
            return 0.0

        num_videos = self.data['video'].num_nodes
        
        for user_id, pos_video_id in interactions:
            u_idx = self.node_mappings['user'].get(user_id)
            v_idx = self.node_mappings['video'].get(pos_video_id)
            
            if u_idx is None or v_idx is None:
                continue

            neg_idx = np.random.randint(0, num_videos)

            embeddings = self.model(self.data.x_dict, self.data.edge_index_dict)
            
            user_emb = embeddings['user'][u_idx]
            pos_emb = embeddings['video'][v_idx]
            neg_emb = embeddings['video'][neg_idx]
            
            # BPR loss
            pos_score = (user_emb * pos_emb).sum()
            neg_score = (user_emb * neg_emb).sum()
            loss = -F.logsigmoid(pos_score - neg_score)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / max(num_batches, 1)
    
    def _extract_and_store_embeddings(self):
        
        self.model.eval()
        with torch.no_grad():
            embeddings = self.model(self.data.x_dict, self.data.edge_index_dict)
            
            # Store each node type
            for node_type in ['user', 'video', 'category', 'parent_category']:
                emb_dict = {}
                
                for node_id, idx in self.node_mappings[node_type].items():
                    emb = embeddings[node_type][idx].cpu().numpy()
                    emb_dict[node_id] = emb
                
                self._store_embeddings_in_neo4j(node_type, emb_dict)

        self._build_faiss_index()
    
    def _store_embeddings_in_neo4j(self, node_type: str, embeddings: Dict[str, np.ndarray]):
        with self.driver.session() as session:
            if node_type == 'parent_category':
                node_label = 'ParentCategory'
                id_field = 'parent_category_id'
            else:
                node_label = node_type.capitalize()
                id_field = f"{node_type}_id"
            
            for node_id, embedding in embeddings.items():
                emb_str = json.dumps(embedding.tolist())
                
                query = f"""
                MATCH (n:{node_label} {{{id_field}: $node_id}})
                SET n.embedding = $embedding,
                    n.embedding_updated = datetime()
                """
                
                session.run(query, node_id = node_id, embedding = emb_str)
    
    def _build_faiss_index(self):

        video_embeddings = []
        self.video_ids = []
        
        # Get video embeddings
        with self.driver.session() as session:
            result = session.run("""
                MATCH (v:Video)
                WHERE v.embedding IS NOT NULL
                RETURN v.video_id as video_id, v.embedding as embedding
            """)
            
            for record in result:
                emb = np.array(json.loads(record['embedding']))
                video_embeddings.append(emb)
                self.video_ids.append(record['video_id'])
        
        if not video_embeddings:
            return
        
        video_embeddings = np.array(video_embeddings).astype('float32')
        faiss.normalize_L2(video_embeddings)

        dimension = video_embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)
        self.faiss_index.add(video_embeddings)

    # RECOMMENDATIONS (Using Trained Embeddings)
    
    def get_recommendations(self, user_id: int, limit: int = 20) -> List[str]:
        
        if self.faiss_index is None:
            self.ensure_model_trained()
        
        with self.driver.session() as session:
            result = session.run('''
                MATCH (u:User {user_id: $user_id})
                RETURN u.embedding as embedding
            ''', user_id = str(user_id))
            
            record = result.single()
            
            if not record or not record['embedding']:
                return self._get_popular_videos(limit)

            user_embedding = np.array(json.loads(record['embedding'])).astype('float32')
            user_embedding = user_embedding.reshape(1, -1)
            faiss.normalize_L2(user_embedding)

            if self.faiss_index is None:
                self._build_faiss_index()
            
            scores, indices = self.faiss_index.search(user_embedding, limit * 2)
            
            # Filter out watched videos
            result = session.run('''
                MATCH (u:User {user_id: $user_id})-[:WATCHES]->(v:Video)
                RETURN v.video_id as video_id
            ''', user_id = str(user_id))
            
            watched = {r['video_id'] for r in result}
            
            recommendations = []
            for idx in indices[0]:
                if idx < len(self.video_ids):
                    video_id = self.video_ids[idx]
                    if video_id not in watched:
                        recommendations.append(video_id)
                        if len(recommendations) >= limit:
                            break
            
            return recommendations
    
    def get_recommendations_from_followed(self, user_id: int, limit: int = 10) -> List[str]:
        with self.driver.session() as session:
            result = session.run('''
                MATCH (u:User {user_id: $user_id})-[:FOLLOWS]->(creator:User)
                WHERE exists((creator)<-[:CREATED_BY]-(:Video))
                MATCH (creator)<-[:CREATED_BY]-(v:Video)
                WHERE NOT exists((u)-[:WATCHES]->(v))
                
                WITH v
                OPTIONAL MATCH (v)<-[w:WATCHES]-()
                WITH v, count(w) as watch_count
                ORDER BY watch_count DESC
                LIMIT $limit
                
                RETURN v.video_id as video_id
            ''', user_id = str(user_id), limit = limit)
            
            return [record['video_id'] for record in result]
    
    def get_recommendations_by_category(self, parent_category_id: str, user_id: Optional[int] = None, limit: int = 20) -> List[str]:
        with self.driver.session() as session:
            if user_id:
                query = '''
                    MATCH (v:Video)
                    WHERE $parent_cat IN v.parent_categories
                      AND NOT exists((:User {user_id: $user_id})-[:WATCHES]->(v))
                    
                    OPTIONAL MATCH (v)<-[w:WATCHES]-()
                    WITH v, count(w) as watch_count
                    ORDER BY watch_count DESC
                    LIMIT $limit
                    
                    RETURN v.video_id as video_id
                '''
                result = session.run(query, parent_cat = parent_category_id, user_id = str(user_id), limit = limit)
            else:
                query = '''
                    MATCH (v:Video)
                    WHERE $parent_cat IN v.parent_categories
                    
                    OPTIONAL MATCH (v)<-[w:WATCHES]-()
                    WITH v, count(w) as watch_count
                    ORDER BY watch_count DESC
                    LIMIT $limit
                    
                    RETURN v.video_id as video_id
                '''
                result = session.run(query, parent_cat = parent_category_id, limit = limit)
            
            return [record['video_id'] for record in result]
    
    def _get_popular_videos(self, limit: int) -> List[str]:
        with self.driver.session() as session:
            result = session.run('''
                MATCH (v:Video)<-[w:WATCHES]-()
                WITH v, count(w) as watch_count
                ORDER BY watch_count DESC
                LIMIT $limit
                RETURN v.video_id as video_id
            ''', limit = limit)
            
            return [record['video_id'] for record in result]

    # STATS SYNC (Neo4j -> Django)

    def get_user_stats(self, user_id: int) -> Dict:
        with self.driver.session() as session:
            result = session.run('''
                MATCH (u:User {user_id: $user_id})
                
                OPTIONAL MATCH (u)<-[:FOLLOWS]-(follower:User)
                WITH u, count(DISTINCT follower) as follower_count
                
                OPTIONAL MATCH (u)-[:FOLLOWS]->(followee:User)
                WITH u, follower_count, count(DISTINCT followee) as following_count
                
                OPTIONAL MATCH (u)<-[:CREATED_BY]-(v:Video)
                
                RETURN follower_count, following_count, count(v) as video_count
            ''', user_id=str(user_id))
            
            record = result.single()
            return {
                'follower_count': record['follower_count'], 'following_count': record['following_count'], 'video_count': record['video_count']}

# Global instance
recommendation_engine = RecommendationEngine()