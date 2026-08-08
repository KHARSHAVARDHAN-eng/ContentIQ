import unittest
from app.services.context_compressor import context_compressor
from app.services.llm_service import llm_service

class AnswerSynthesisQualityTest(unittest.TestCase):

    def test_chunk_beginning_mid_sentence_cleanup(self):
        # Test boundary cleaning on leading partial word/sentence fragments (e.g. 'ana later left...')
        raw_text = "ana later left the hut after hearing a deceptive cry. Ravana seized the opportunity to abduct Sita."
        cleaned = context_compressor._clean_chunk_boundaries(raw_text)
        
        # Verify leading broken sentence fragment is discarded and text starts cleanly with 'Ravana'
        self.assertFalse(cleaned.startswith("ana "))
        self.assertFalse(cleaned.startswith("Later "))
        self.assertTrue(cleaned.startswith("Ravana seized"))

    def test_chunk_ending_mid_sentence_cleanup(self):
        # Test boundary cleaning on trailing unpunctuated sentence fragments
        raw_text = "Maricha disguised himself as a golden deer. Sita requested the deer and Lakshmana"
        cleaned = context_compressor._clean_chunk_boundaries(raw_text)
        
        # Verify unpunctuated trailing fragment 'and Lakshmana' is trimmed to full sentence boundary
        self.assertEqual(cleaned, "Maricha disguised himself as a golden deer.")

    def test_mock_answer_synthesis_no_broken_fragments(self):
        # Test LLM mock answer synthesis with broken input fragments
        context_chunks = [
            {
                "document_name": "Ramayana_Test.pdf",
                "page_number": 5,
                "chunk_id": "1380",
                "chunk_text": "ana later left the hut after hearing a deceptive cry. Ravana seized the opportunity to abduct Sita."
            },
            {
                "document_name": "Ramayana_Test.pdf",
                "page_number": 6,
                "chunk_id": "1382",
                "chunk_text": "Maricha disguised himself as a golden deer to lure Rama away."
            }
        ]
        
        ans = llm_service._generate_mock_answer("Who kidnapped Sita?", context_chunks)
        
        # Must start cleanly with complete sentence starting with Ravana
        self.assertFalse(ans.startswith("ana "))
        self.assertFalse(ans.startswith("According to"))
        self.assertTrue(ans.startswith("Ravana seized"))
        # Must not duplicate exact sentences
        self.assertEqual(ans.count("Ravana seized the opportunity to abduct Sita"), 1)

    def test_query_aware_evidence_selection_abduction(self):
        # Test that abduction query only selects abduction evidence and excludes irrelevant Hanuman/Jatayu context
        context_chunks = [
            {
                "document_name": "Ramayana_Test.pdf",
                "page_number": 5,
                "chunk_id": "1380",
                "chunk_text": "Ravana seized the opportunity to abduct Sita. Maricha disguised himself as a golden deer to lure Rama away."
            },
            {
                "document_name": "Ramayana_Test.pdf",
                "page_number": 8,
                "chunk_id": "1401",
                "chunk_text": "Hanuman discovered Sita in Ashoka Vatika, conveyed Rama's message, and set parts of Lanka ablaze."
            },
            {
                "document_name": "Ramayana_Test.pdf",
                "page_number": 6,
                "chunk_id": "1384",
                "chunk_text": "The noble bird Jatayu bravely fought Ravana in an attempt to rescue Sita."
            }
        ]
        
        question = "Who kidnapped Sita and how did it happen?"
        ans = llm_service._generate_mock_answer(question, context_chunks)
        
        # Must contain Ravana abduction details
        self.assertIn("Ravana", ans)
        self.assertIn("abduct", ans.lower())
        
        # Must NOT append irrelevant Hanuman / Lanka / Jatayu facts
        self.assertNotIn("Ashoka Vatika", ans)
        self.assertNotIn("ablaze", ans.lower())
        self.assertNotIn("Jatayu", ans)

    def test_generic_acme_corp_acquisition(self):
        # Document-agnostic test: Acme Corp acquisition query
        context_chunks = [
            {
                "document_name": "Financial_Report.pdf",
                "page_number": 1,
                "chunk_id": "1",
                "chunk_text": "Acme Corp acquired Beta Ltd for $2 billion in 2025."
            },
            {
                "document_name": "Financial_Report.pdf",
                "page_number": 2,
                "chunk_id": "2",
                "chunk_text": "Acme Corp later opened a research center in London."
            },
            {
                "document_name": "Financial_Report.pdf",
                "page_number": 3,
                "chunk_id": "3",
                "chunk_text": "Beta Ltd previously employed 4,000 people."
            }
        ]
        
        question = "How much did Acme Corp pay to acquire Beta Ltd?"
        ans = llm_service._generate_mock_answer(question, context_chunks)
        
        # Must directly answer $2 billion
        self.assertIn("$2 billion", ans)
        
        # Must NOT include irrelevant London or employee count information
        self.assertNotIn("London", ans)
        self.assertNotIn("4,000", ans)

    def test_supporting_citation_filtering(self):
        # Test that citations only include supporting chunks, filtering out irrelevant retrieved chunks
        context_chunks = [
            {
                "document_name": "Financial_Report.pdf",
                "page_number": 1,
                "chunk_id": "1",
                "chunk_text": "Acme Corp acquired Beta Ltd for $2 billion in 2025."
            },
            {
                "document_name": "Financial_Report.pdf",
                "page_number": 2,
                "chunk_id": "2",
                "chunk_text": "Acme Corp later opened a research center in London."
            }
        ]
        
        answer = "Acme Corp acquired Beta Ltd for $2 billion in 2025."
        sources = llm_service._compile_sources(context_chunks, answer)
        
        # Only page 1 (chunk 1) should be in supporting citations
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["page_number"], 1)

    def test_out_of_scope_question(self):
        # Test handling of out-of-scope question with empty context
        ans = llm_service._generate_mock_answer("What is quantum entanglement?", [])
        self.assertIn("couldn't find information", ans.lower())

    def test_unrelated_query_rejection_capital_of_france(self):
        # Test that out-of-domain query 'What is the capital of France?' returns refusal when context contains Ramayana text
        context_chunks = [
            {
                "document_name": "Ramayana_23_Page_Test_Document.pdf",
                "page_number": 14,
                "chunk_id": "140",
                "chunk_text": "The epic has inspired literature, music, dance, theater, and visual arts across South and Southeast Asia.",
                "score": 0.05
            }
        ]
        ans = llm_service._generate_mock_answer("What is the capital of France?", context_chunks)
        self.assertIn("couldn't find information", ans.lower())
        
        sources = llm_service._compile_sources(context_chunks, ans)
        self.assertEqual(len(sources), 0)

    def test_unrelated_queries_rejection_suite(self):
        # Test 3 additional unrelated queries against irrelevant context
        context_chunks = [
            {
                "document_name": "Ramayana_23_Page_Test_Document.pdf",
                "page_number": 14,
                "chunk_id": "140",
                "chunk_text": "The epic has inspired literature, music, dance, theater, and visual arts across South and Southeast Asia.",
                "score": 0.02
            }
        ]
        unrelated_queries = [
            "What is the formula for quantum entanglement?",
            "Who won the 2024 FIFA World Cup?",
            "How do I bake a chocolate cake?"
        ]
        for q in unrelated_queries:
            ans = llm_service._generate_mock_answer(q, context_chunks)
            self.assertIn("couldn't find information", ans.lower(), f"Failed to reject query: {q}")
            sources = llm_service._compile_sources(context_chunks, ans)
            self.assertEqual(len(sources), 0, f"Sources should be empty for query: {q}")

if __name__ == "__main__":
    unittest.main()

