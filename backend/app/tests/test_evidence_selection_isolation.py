import unittest
from unittest.mock import patch
from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.vector_store import vector_store

class EvidenceSelectionIsolationTest(unittest.TestCase):

    def test_evidence_selection_enabled_default(self):
        # Default behavior: EVIDENCE_SELECTION_ENABLED is True
        self.assertTrue(settings.EVIDENCE_SELECTION_ENABLED)
        
        chunks = [
            {
                "chunk_id": "1",
                "document_id": 1,
                "document_name": "Test.pdf",
                "page_number": 1,
                "chunk_text": "Sugriva formed an alliance with Rama and sent search parties to locate Sita.",
                "score": 0.95
            },
            {
                "chunk_id": "2",
                "document_id": 1,
                "document_name": "Test.pdf",
                "page_number": 2,
                "chunk_text": "Hanuman leaped across the ocean to Lanka and found Sita in Ashoka Vatika.",
                "score": 0.90
            }
        ]
        
        # Focused Sugriva question: Evidence selector should drop Hanuman sentence (chunk 2)
        res = llm_service.generate_answer("How did Sugriva help Rama find Sita?", chunks)
        ans = res["answer"]
        self.assertNotIn("Ashoka Vatika", ans)

    def test_evidence_selection_disabled_bypass(self):
        # When EVIDENCE_SELECTION_ENABLED is set to False, evidence selector is bypassed
        original_setting = settings.EVIDENCE_SELECTION_ENABLED
        try:
            settings.EVIDENCE_SELECTION_ENABLED = False
            
            chunks = [
                {
                    "chunk_id": "1",
                    "document_id": 1,
                    "document_name": "Test.pdf",
                    "page_number": 1,
                    "chunk_text": "Sugriva formed an alliance with Rama and sent search parties to locate Sita.",
                    "score": 0.95
                },
                {
                    "chunk_id": "2",
                    "document_id": 1,
                    "document_name": "Test.pdf",
                    "page_number": 2,
                    "chunk_text": "Hanuman leaped across the ocean to Lanka and found Sita in Ashoka Vatika.",
                    "score": 0.90
                }
            ]
            
            # Focused Sugriva question with evidence selection OFF: both chunks should remain in synthesis
            res = llm_service.generate_answer("How did Sugriva help Rama find Sita?", chunks)
            ans = res["answer"]
            self.assertIn("Sugriva", ans)
            self.assertIn("Ashoka Vatika", ans)
        finally:
            settings.EVIDENCE_SELECTION_ENABLED = original_setting

    def test_qdrant_collection_isolation(self):
        # Verify vector_store supports creating and searching isolated collections (e.g. research_fixed vs research_adaptive)
        try:
            vector_store.client.delete_collection("research_fixed")
        except Exception:
            pass
        try:
            vector_store.client.delete_collection("research_adaptive")
        except Exception:
            pass
        vector_store.create_collection(collection_name="research_fixed", vector_size=384)
        vector_store.create_collection(collection_name="research_adaptive", vector_size=384)
        
        # Points for research_fixed
        vector_store.upsert_chunk(
            chunk_id=101,
            document_id=1,
            page_number=1,
            chunk_text="Fixed 500-token chunk snippet for Baseline 1.",
            vector=[0.1] * 384,
            collection_name="research_fixed"
        )
        
        # Points for research_adaptive
        vector_store.upsert_chunk(
            chunk_id=201,
            document_id=2,
            page_number=1,
            chunk_text="Adaptive document chunk snippet for Baselines 2-5.",
            vector=[0.1] * 384,
            collection_name="research_adaptive"
        )
        
        # Search research_fixed: must only return chunk 101
        hits_fixed = vector_store.search_similar_chunks(
            query_vector=[0.1] * 384,
            limit=5,
            collection_name="research_fixed"
        )
        self.assertEqual(len(hits_fixed), 1)
        self.assertEqual(hits_fixed[0]["chunk_id"], 101)
        self.assertIn("Fixed 500-token", hits_fixed[0]["chunk_text"])
        
        # Search research_adaptive: must only return chunk 201
        hits_adaptive = vector_store.search_similar_chunks(
            query_vector=[0.1] * 384,
            limit=5,
            collection_name="research_adaptive"
        )
        self.assertEqual(len(hits_adaptive), 1)
        self.assertEqual(hits_adaptive[0]["chunk_id"], 201)
        self.assertIn("Adaptive document", hits_adaptive[0]["chunk_text"])

if __name__ == "__main__":
    unittest.main()
