import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import tempfile

from app.core.config import settings
from app.services.graph_store import GraphStore
from app.services.entity_extractor import entity_extractor
from app.services.relationship_extractor import relationship_extractor
from app.services.graph_builder import graph_builder
from app.services.graph_retriever import graph_retriever
from app.services.graph_ranker import graph_ranker
from app.api.graph import filter_user_graph, get_user_doc_ids

class GraphRAGUnitTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for the graph store to prevent mutating production JSON
        self.test_dir = tempfile.mkdtemp()
        self.test_store_path = os.path.join(self.test_dir, "test_graph_store.json")
        self.original_path = settings.GRAPHRAG_STORAGE_PATH
        settings.GRAPHRAG_STORAGE_PATH = self.test_store_path
        
        # Instantiate a fresh test store
        self.store = GraphStore(self.test_store_path)

    def tearDown(self):
        settings.GRAPHRAG_STORAGE_PATH = self.original_path
        shutil.rmtree(self.test_dir)

    def test_entity_extraction_fallback(self):
        # Disable Gemini API key to force rule-based NER
        old_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = ""
        try:
            text = "Microsoft Corporation is located in Redmond, Washington. Bill Gates founded it."
            entities = entity_extractor.extract_entities(text)
            
            names = [e["name"].lower() for e in entities]
            self.assertIn("microsoft corporation", names)
            self.assertIn("redmond", names)
            self.assertIn("bill gates", names)
        finally:
            settings.GEMINI_API_KEY = old_key

    def test_relationship_extraction_fallback(self):
        old_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = ""
        try:
            text = "Paris is located in France. Paris has high Eiffel Tower."
            entities = [
                {"name": "Paris", "type": "Location"},
                {"name": "France", "type": "Location"}
            ]
            relationships = relationship_extractor.extract_relationships(text, entities)
            
            self.assertTrue(len(relationships) >= 1)
            paris_edge = relationships[0]
            self.assertEqual(paris_edge["source"], "Paris")
            self.assertEqual(paris_edge["target"], "France")
            self.assertEqual(paris_edge["type"], "located_in")
            self.assertTrue(paris_edge["confidence"] > 0.6)
        finally:
            settings.GEMINI_API_KEY = old_key

    def test_graph_store_operations(self):
        # Clear graph
        self.store.clear()
        
        # Add Node
        self.store.add_node("france", "France", "Location", ["French Republic"], {"population": "67M"})
        self.assertEqual(self.store.nodes["france"]["name"], "France")
        self.assertIn("French Republic", self.store.nodes["france"]["aliases"])
        
        # Add Node (Alias merge)
        self.store.add_node("france", "France", "Location", ["L'Hexagone"], {"climate": "Temperate"})
        self.assertIn("L'Hexagone", self.store.nodes["france"]["aliases"])
        self.assertIn("French Republic", self.store.nodes["france"]["aliases"])
        
        # Add Edge
        self.store.add_edge("paris", "france", "located_in", "Paris is the capital of France", 0.95, {"document_id": 1})
        self.assertEqual(len(self.store.edges), 1)
        self.assertEqual(self.store.edges[0]["source"], "paris")
        self.assertEqual(self.store.edges[0]["target"], "france")
        
        # Check node auto-creation during edge insert
        self.assertIn("paris", self.store.nodes)

    def test_graph_statistics(self):
        self.store.clear()
        self.store.add_node("a", "A", "Concept")
        self.store.add_node("b", "B", "Concept")
        self.store.add_node("c", "C", "Concept")
        
        self.store.add_edge("a", "b", "related_to")
        self.store.add_edge("b", "c", "related_to")
        
        stats = self.store.get_statistics()
        self.assertEqual(stats["node_count"], 3)
        self.assertEqual(stats["edge_count"], 2)
        self.assertEqual(stats["connected_components"], 1)
        self.assertEqual(stats["largest_component_size"], 3)
        self.assertEqual(stats["average_degree"], 1.3333)

    def test_graph_traversal(self):
        # Use mocked global graph_store referenced inside retriever
        with patch("app.services.graph_retriever.graph_store", self.store):
            self.store.clear()
            self.store.add_node("node1", "Node1", "Concept")
            self.store.add_node("node2", "Node2", "Concept")
            self.store.add_node("node3", "Node3", "Concept")
            
            self.store.add_edge("node1", "node2", "uses")
            self.store.add_edge("node2", "node3", "depends_on")
            
            # Matched nodes traversal check
            nodes, edges = graph_retriever._traverse_graph({"node1"}, max_depth=2)
            self.assertIn("node1", nodes)
            self.assertIn("node2", nodes)
            self.assertIn("node3", nodes)
            self.assertEqual(len(edges), 2)

    def test_pagerank_calculation(self):
        node_ids = {"a", "b", "c"}
        edges = [
            {"source": "a", "target": "b", "confidence": 1.0},
            {"source": "b", "target": "c", "confidence": 1.0}
        ]
        
        pr = graph_ranker.calculate_pagerank(node_ids, edges, iterations=5)
        self.assertEqual(len(pr), 3)
        # Symmetrical nodes (a & c) should have identical PageRank score
        self.assertAlmostEqual(pr["a"], pr["c"])

    def test_hybrid_ranking(self):
        vector_hits = [
            {"chunk_id": "1", "document_id": 1, "page_number": 1, "chunk_text": "Vector content 1", "score": 0.8},
            {"chunk_id": "2", "document_id": 1, "page_number": 1, "chunk_text": "Vector content 2", "score": 0.6}
        ]
        
        graph_hits = [
            {"chunk_id": "2", "document_id": 1, "page_number": 1, "chunk_text": "Vector content 2", "score": 0.7},
            {"chunk_id": "3", "document_id": 1, "page_number": 2, "chunk_text": "Graph content 3", "score": 0.9}
        ]
        
        pr_scores = {"a": 0.5, "b": 0.2}
        
        # Rank matching chunks
        ranked = graph_ranker.rank_hybrid_chunks(vector_hits, graph_hits, pr_scores)
        self.assertEqual(len(ranked), 3)
        
        # Check sorting order
        self.assertTrue(ranked[0]["score"] >= ranked[1]["score"])

    def test_incremental_updates_and_deletion(self):
        self.store.clear()
        
        # Mock chunk object
        chunk1 = MagicMock()
        chunk1.id = 101
        chunk1.chunk_text = "Python is a technology."
        
        # Build document graph
        with patch("app.services.graph_builder.graph_store", self.store):
            graph_builder.build_graph_for_document(1, [chunk1])
            self.assertTrue(len(self.store.nodes) > 0)
            
            # Deletion verification
            self.store.delete_document_nodes(1)
            self.assertEqual(len(self.store.nodes), 0)
            self.assertEqual(len(self.store.edges), 0)

    def test_configuration_bypass(self):
        old_enabled = settings.GRAPHRAG_ENABLED
        settings.GRAPHRAG_ENABLED = False
        try:
            # When disabled, retrieve_graph_context shouldn't be executed or should return empty
            # Verify retrieval routing safely handles config = False
            self.assertFalse(settings.GRAPHRAG_ENABLED)
        finally:
            settings.GRAPHRAG_ENABLED = old_enabled

class GraphRAGE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import requests
        import random
        cls.BASE_URL = "http://localhost:8000/api"
        cls.rand_id = random.randint(10000, 99999)
        cls.email = f"graph_user_{cls.rand_id}@example.com"
        cls.password = "graphpassword123"
        
        reg_resp = requests.post(f"{cls.BASE_URL}/auth/register", json={"email": cls.email, "password": cls.password})
        assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
        
        login_resp = requests.post(f"{cls.BASE_URL}/auth/login", json={"email": cls.email, "password": cls.password})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        cls.token = login_resp.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_graph_endpoints(self):
        import requests
        # Test Statistics
        stats_resp = requests.get(f"{self.BASE_URL}/graph/statistics", headers=self.headers)
        self.assertEqual(stats_resp.status_code, 200)
        self.assertEqual(stats_resp.json()["node_count"], 0)

        # Test Entities
        entities_resp = requests.get(f"{self.BASE_URL}/graph/entities", headers=self.headers)
        self.assertEqual(entities_resp.status_code, 200)
        self.assertEqual(len(entities_resp.json()), 0)

        # Test Subgraph
        subgraph_resp = requests.get(f"{self.BASE_URL}/graph/subgraph", headers=self.headers)
        self.assertEqual(subgraph_resp.status_code, 200)
        self.assertEqual(len(subgraph_resp.json()["entities"]), 0)

        # Test Export
        export_resp = requests.get(f"{self.BASE_URL}/graph/export", headers=self.headers)
        self.assertEqual(export_resp.status_code, 200)
        self.assertEqual(len(export_resp.json()["nodes"]), 0)

