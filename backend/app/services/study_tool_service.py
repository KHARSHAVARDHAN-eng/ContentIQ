import json
import logging
import google.generativeai as genai
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger("app.services.study_tool_service")

class StudyToolService:
    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    def generate_flashcards(self, document_name: str, document_text: str) -> List[Dict[str, str]]:
        """
        Sends the document text to Gemini to generate flashcard Q&A pairs.
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Using local mock generator for flashcards.")
            return self._generate_mock_flashcards(document_name)

        # Truncate document text to avoid exceeding prompt limitations (approx. 80k chars)
        max_chars = 80000
        truncated_text = document_text
        if len(document_text) > max_chars:
            truncated_text = document_text[:max_chars] + "\n\n... [Text Truncated for Ingestion Limits] ..."

        try:
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an expert academic tutor and study assistant.\n"
                "Your goal is to extract the most important information, concepts, definitions, formulas, "
                "and arguments from the provided text and formulate them as high-quality flashcards (Question/Answer pairs).\n"
                "Ensure the questions are specific and clear, and the answers are concise, accurate, and educational."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )

            prompt = (
                f"Document Name: {document_name}\n"
                f"Document Content:\n"
                f"=====================\n"
                f"{truncated_text}\n"
                f"=====================\n\n"
                f"Instructions:\n"
                f"Based ONLY on the document context above, generate a list of 8 to 12 flashcards. "
                f"Make sure they test key facts, terminology, formulas, and concepts. "
                f"Format the output strictly as a JSON object with a single 'cards' key containing a list of cards, like this:\n"
                f"{{\n"
                f"  \"cards\": [\n"
                f"    {{\n"
                f"      \"question\": \"Question text here?\",\n"
                f"      \"answer\": \"Detailed answer text here.\"\n"
                f"    }}\n"
                f"  ]\n"
                f"}}\n"
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text.strip())
            return result.get("cards", [])

        except Exception as e:
            logger.error(f"Gemini flashcard generation failed: {e}", exc_info=True)
            # Fallback to mock flashcards
            return self._generate_mock_flashcards(document_name)

    def generate_mcqs(self, document_name: str, document_text: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
        """
        Sends the document text to Gemini to generate multiple choice questions.
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Using local mock generator for MCQs.")
            return self._generate_mock_mcqs(document_name, difficulty, count)

        # Truncate document text to avoid exceeding prompt limitations
        max_chars = 80000
        truncated_text = document_text
        if len(document_text) > max_chars:
            truncated_text = document_text[:max_chars] + "\n\n... [Text Truncated for Ingestion Limits] ..."

        try:
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an expert test creator and assessor.\n"
                "Your goal is to generate challenging, accurate multiple-choice questions (MCQs) "
                "based on the provided text, tailored to a specific difficulty level."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )

            difficulty_guide = ""
            if difficulty.lower() == "easy":
                difficulty_guide = "Easy difficulty: focus on direct recall, basic definitions, and simple facts."
            elif difficulty.lower() == "medium":
                difficulty_guide = "Medium difficulty: focus on conceptual comprehension, explanation of relationships, and application of principles."
            else:
                difficulty_guide = "Hard difficulty: focus on critical analysis, synthesis of multiple ideas, evaluation, and edge-cases/complex inferences."

            prompt = (
                f"Document Name: {document_name}\n"
                f"Document Content:\n"
                f"=====================\n"
                f"{truncated_text}\n"
                f"=====================\n\n"
                f"Instructions:\n"
                f"Generate exactly {count} multiple-choice questions from the content above.\n"
                f"Difficulty level to target: {difficulty.upper()}.\n"
                f"{difficulty_guide}\n\n"
                f"For each question, provide:\n"
                f"- The question string.\n"
                f"- A list of exactly 4 choices labelled A, B, C, D (format option prefix as 'A) ', 'B) ', 'C) ', 'D) ').\n"
                f"- The correct answer indicator ('A', 'B', 'C', or 'D').\n"
                f"- A detailed, friendly explanation explaining why the correct choice is correct and why others are incorrect.\n\n"
                f"Format the output strictly as a JSON object with a single 'mcqs' key containing the list, like this:\n"
                f"{{\n"
                f"  \"mcqs\": [\n"
                f"    {{\n"
                f"      \"question\": \"Question text here?\",\n"
                f"      \"options\": [\n"
                f"        \"A) Option text 1\",\n"
                f"        \"B) Option text 2\",\n"
                f"        \"C) Option text 3\",\n"
                f"        \"D) Option text 4\"\n"
                f"      ],\n"
                f"      \"correct_answer\": \"B\",\n"
                f"      \"explanation\": \"Detailed explanation here.\"\n"
                f"    }}\n"
                f"  ]\n"
                f"}}\n"
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text.strip())
            return result.get("mcqs", [])

        except Exception as e:
            logger.error(f"Gemini MCQ generation failed: {e}", exc_info=True)
            return self._generate_mock_mcqs(document_name, difficulty, count)

    def _generate_mock_flashcards(self, document_name: str) -> List[Dict[str, str]]:
        return [
            {
                "question": f"What is the main theme of '{document_name}'?",
                "answer": "This document explores core architectural schemas, business intelligence analysis, or technical implementation frameworks."
            },
            {
                "question": "What is the primary benefit of using a local database format?",
                "answer": "Using a local database format like SQLite simplifies development, prevents network roundtrips, and provides fast local state serialization."
            },
            {
                "question": "How are semantic relationships managed in basic documents?",
                "answer": "Semantic relationships are mapped using tokenized paragraphs, text splitters, embedding engines, and vector similarity dimensions."
            },
            {
                "question": "What does a high OCR confidence score indicate?",
                "answer": "A high OCR confidence score indicates that the document parser was highly accurate in mapping image pixels to text characters."
            },
            {
                "question": "Why is context grounding important for LLMs?",
                "answer": "Context grounding limits the scope of LLM generations to verified facts in source documents, preventing hallucinations and inaccurate outputs."
            }
        ]

    def _generate_mock_mcqs(self, document_name: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
        all_mocks = [
            {
                "question": f"Which of the following describes the status of the document '{document_name}'?",
                "options": [
                    "A) It is currently parsed and vectorized in the system databases.",
                    "B) It is unreadable by any semantic processors.",
                    "C) It is stored entirely inside external memory servers.",
                    "D) It requires manual validation before any prompt operations."
                ],
                "correct_answer": "A",
                "explanation": "Once a document upload is complete, DocumentIQ automatically triggers parsing, OCR evaluation, chunk splits, and vector storage."
            },
            {
                "question": "What is the primary role of the vector store in RAG pipelines?",
                "options": [
                    "A) To compress user sign-on credentials.",
                    "B) To execute cosine similarity matches on chunk embeddings for fast contextual queries.",
                    "C) To format raw HTML tables into markdown format.",
                    "D) To backup PDF files on regional remote servers."
                ],
                "correct_answer": "B",
                "explanation": "Vector databases like Qdrant index semantic dimensions to quickly fetch document chunks relevant to user questions."
            },
            {
                "question": "When configuring generative settings, why is temperature set close to zero?",
                "options": [
                    "A) To speed up execution duration by compiling cache items.",
                    "B) To enforce strict grounding and minimize creative hallucinations in responses.",
                    "C) To decrease database storage footprint.",
                    "D) To reduce model parameter sizes dynamically."
                ],
                "correct_answer": "B",
                "explanation": "Low temperature parameters constrain generative models to be highly deterministic and focused on context."
            },
            {
                "question": "Which metadata indicator is crucial for validating OCR accuracy?",
                "options": [
                    "A) File size on disk",
                    "B) OCR confidence percentage",
                    "C) The page length count",
                    "D) User ID foreign keys"
                ],
                "correct_answer": "B",
                "explanation": "The OCR confidence metric determines the clarity and correctness of text extraction from images or scan scans."
            },
            {
                "question": "What is the recommended range for semantic text chunk sizes?",
                "options": [
                    "A) 1-2 words",
                    "B) 300-600 tokens or characters depending on document structure and model boundaries",
                    "C) Exactly 100 pages of content",
                    "D) Variable lines under 5 words"
                ],
                "correct_answer": "B",
                "explanation": "A balanced chunk size ensures paragraphs retain semantic meaning without overflowing LLM context limits."
            }
        ]
        # Return slice matching count
        return all_mocks[:count]

    def generate_mindmap(self, document_name: str, document_text: str) -> Dict[str, Any]:
        """
        Sends the document text to Gemini to generate a conceptual mindmap hierarchy.
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Using local mock generator for mindmaps.")
            return self._generate_mock_mindmap(document_name)

        # Truncate text to fit limitations
        max_chars = 80000
        truncated_text = document_text
        if len(document_text) > max_chars:
            truncated_text = document_text[:max_chars] + "\n\n... [Text Truncated for Ingestion Limits] ..."

        try:
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an expert educational designer who specializes in creating clear, structured, "
                "hierarchical concept mind maps to help users memorize and study complex subjects.\n"
                "Your goal is to break down the provided text into a logical hierarchy of ideas:\n"
                "1. A central subject (the root node).\n"
                "2. Three to five main concepts/subtopics (level 1 child nodes).\n"
                "3. Each subtopic should have two to four key details, definitions, or context points (level 2 child nodes).\n"
                "Keep labels concise (1-4 words) and descriptions short (under 15 words) and clear.\n"
                "Format IDs as simple unique strings, e.g. 'node-1', 'node-1-1'."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )

            prompt = (
                f"Document Name: {document_name}\n"
                f"Document Content:\n"
                f"=====================\n"
                f"{truncated_text}\n"
                f"=====================\n\n"
                f"Instructions:\n"
                f"Extract a comprehensive concept mindmap from the document contents.\n"
                f"Ensure it contains a root node, 3 to 5 main branch nodes, and 2 to 4 key detail nodes under each branch.\n\n"
                f"Format the output strictly as a JSON object fitting the following structure:\n"
                f"{{\n"
                f"  \"title\": \"Mindmap Title\",\n"
                f"  \"root\": {{\n"
                f"    \"id\": \"root\",\n"
                f"    \"label\": \"Central Subject Name\",\n"
                f"    \"description\": \"Summary of central subject\",\n"
                f"    \"children\": [\n"
                f"      {{\n"
                f"        \"id\": \"node-1\",\n"
                f"        \"label\": \"Branch Name\",\n"
                f"        \"description\": \"Branch description\",\n"
                f"        \"children\": [\n"
                f"          {{\n"
                f"            \"id\": \"node-1-1\",\n"
                f"            \"label\": \"Detail Name\",\n"
                f"            \"description\": \"Detail description\"\n"
                f"          }}\n"
                f"        ]\n"
                f"      }}\n"
                f"    ]\n"
                f"  }}\n"
                f"}}\n"
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text.strip())
            return result

        except Exception as e:
            logger.error(f"Gemini mindmap generation failed: {e}", exc_info=True)
            return self._generate_mock_mindmap(document_name)

    def _generate_mock_mindmap(self, document_name: str) -> Dict[str, Any]:
        return {
            "title": f"Concept Mindmap: {document_name}",
            "root": {
                "id": "root",
                "label": document_name,
                "description": "Core concepts extracted from the uploaded source document.",
                "children": [
                    {
                        "id": "m1",
                        "label": "Document Ingestion",
                        "description": "Key semantic metadata and storage configuration.",
                        "children": [
                            {
                                "id": "m1-1",
                                "label": "Text Parsing",
                                "description": "Files are parsed, cleaned, and split into chunks of fixed overlaps."
                            },
                            {
                                "id": "m1-2",
                                "label": "OCR Scanning",
                                "description": "Converts image pixels to readable text characters with confidence scores."
                            }
                        ]
                    },
                    {
                        "id": "m2",
                        "label": "RAG Pipeline",
                        "description": "Semantic searching and content generation pipeline.",
                        "children": [
                            {
                                "id": "m2-1",
                                "label": "Qdrant Vector DB",
                                "description": "Dense vectors generated using SentenceTransformers to map document similarities."
                            },
                            {
                                "id": "m2-2",
                                "label": "Prompt Grounding",
                                "description": "Constrains LLM queries to extracted document facts, preventing hallucinations."
                            }
                        ]
                    },
                    {
                        "id": "m3",
                        "label": "RAG Evaluation",
                        "description": "System health and quality parameters of LLM output.",
                        "children": [
                            {
                                "id": "m3-1",
                                "label": "Context Precision",
                                "description": "Verifies that all retrieved text chunks are highly relevant to the query."
                            },
                            {
                                "id": "m3-2",
                                "label": "Faithfulness & Latency",
                                "description": "Measures response time in milliseconds and verifies output facts against source chunks."
                            }
                        ]
                    }
                ]
            }
        }

    def generate_summary(self, document_name: str, document_text: str) -> Dict[str, Any]:
        """
        Sends the document text to Gemini to generate an executive summary and key takeaways.
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Using local mock generator for summary.")
            return self._generate_mock_summary(document_name)

        # Truncate text to fit limitations
        max_chars = 80000
        truncated_text = document_text
        if len(document_text) > max_chars:
            truncated_text = document_text[:max_chars] + "\n\n... [Text Truncated for Ingestion Limits] ..."

        try:
            genai.configure(api_key=api_key)
            
            system_instruction = (
                "You are an expert technical writer and education assistant.\n"
                "Your goal is to extract the primary concepts of the provided text and summarize them concisely.\n"
                "You should output:\n"
                "1. A clear, cohesive executive summary (around 150-250 words).\n"
                "2. A list of 4 to 6 key takeaways (under 20 words each) for easy memorization."
            )
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )

            prompt = (
                f"Document Name: {document_name}\n"
                f"Document Content:\n"
                f"=====================\n"
                f"{truncated_text}\n"
                f"=====================\n\n"
                f"Instructions:\n"
                f"Generate a clear summary and key takeaways based only on the content above.\n\n"
                f"Format the output strictly as a JSON object with 'summary' and 'takeaways' keys like this:\n"
                f"{{\n"
                f"  \"summary\": \"Executive summary text...\",\n"
                f"  \"takeaways\": [\n"
                f"    \"Takeaway item 1...\",\n"
                f"    \"Takeaway item 2...\"\n"
                f"  ]\n"
                f"}}\n"
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text.strip())
            return result

        except Exception as e:
            logger.error(f"Gemini summary generation failed: {e}", exc_info=True)
            return self._generate_mock_summary(document_name)

    def _generate_mock_summary(self, document_name: str) -> Dict[str, Any]:
        return {
            "summary": (
                f"This document, titled '{document_name}', presents a comprehensive analysis of RAG intelligence pipelines, "
                "document processing rules, and evaluation logging schemas. It explores how context chunks are indexed, "
                "vectorized, and matched inside Qdrant vector databases, alongside custom security validation configurations."
            ),
            "takeaways": [
                "Spaced repetition and active recall (flashcards, MCQs) dramatically increase conceptual understanding.",
                "Document ingestion handles custom chunking sizes with page-level OCR confidence scoring.",
                "Vector retrieval pipelines search matching document nodes using dense embeddings sizes.",
                "Faithfulness and relevancy metrics assure high LLM answer quality."
            ]
        }

    def draw_mindmap_png(self, mindmap_data: Dict[str, Any]) -> bytes:
        """
        Uses Pillow to draw connection curves and node blocks for the Mind Map, returning PNG bytes.
        """
        from PIL import Image, ImageDraw, ImageFont
        import io

        # Layout recursive tree
        root = mindmap_data.get("root", {})
        if not root:
            img = Image.new("RGB", (200, 200), (255, 255, 255))
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue()

        nodes = []
        edges = []

        level_width = 280
        leaf_spacing = 90

        def get_subtree_height(n):
            if not n.get("children"):
                return 1
            return sum(get_subtree_height(child) for child in n["children"])

        def assign_coordinates(n, depth, y_start):
            subtree_height = get_subtree_height(n)
            total_height = subtree_height * leaf_spacing
            y = y_start + total_height / 2 - leaf_spacing / 2
            x = depth * level_width + 40

            node_data = {
                "id": n.get("id"),
                "label": n.get("label", "Node"),
                "description": n.get("description", ""),
                "depth": depth,
                "x": x,
                "y": y
            }
            nodes.append(node_data)

            if n.get("children"):
                current_y_start = y_start
                for child in n["children"]:
                    child_height = get_subtree_height(child) * leaf_spacing
                    child_coords = assign_coordinates(child, depth + 1, current_y_start)
                    edges.append({
                        "source": (x, y),
                        "target": (child_coords["x"], child_coords["y"])
                    })
                    current_y_start += child_height

            return {"x": x, "y": y}

        assign_coordinates(root, 0, 40)

        max_x = max(node["x"] for node in nodes) + 250
        max_y = max(node["y"] for node in nodes) + 100

        # Create image
        img = Image.new("RGB", (int(max_x), int(max_y)), (244, 244, 245))
        draw = ImageDraw.Draw(img)

        # Load macOS fonts
        def get_font_by_size(size):
            for font_path in [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Helvetica.ttf"
            ]:
                try:
                    return ImageFont.truetype(font_path, size)
                except IOError:
                    continue
            return ImageFont.load_default()

        title_font = get_font_by_size(12)
        desc_font = get_font_by_size(8)

        # Draw lines
        for edge in edges:
            startX = edge["source"][0] + 190
            startY = edge["source"][1] + 25
            endX = edge["target"][0]
            endY = edge["target"][1] + 25
            draw.line([startX, startY, endX, endY], fill=(212, 212, 216), width=2)

        # Draw nodes
        for node in nodes:
            x, y = node["x"], node["y"]
            depth = node["depth"]
            label = node["label"]
            desc = node["description"]

            if depth == 0:
                # Core theme: Dark slate box
                draw.rectangle([x, y, x + 190, y + 50], fill=(24, 24, 27), outline=(39, 39, 42))
                draw.text((x + 10, y + 10), "Theme Root", fill=(161, 161, 170), font=desc_font)
                draw.text((x + 10, y + 26), label[:28], fill=(255, 255, 255), font=title_font)
            elif depth == 1:
                # Subtopic branches: White box with sky blue border accent
                draw.rectangle([x, y, x + 190, y + 50], fill=(255, 255, 255), outline=(228, 228, 231))
                draw.rectangle([x, y, x + 5, y + 50], fill=(14, 165, 233))
                draw.text((x + 15, y + 10), label[:28], fill=(24, 24, 27), font=title_font)
                if desc:
                    draw.text((x + 15, y + 28), desc[:35], fill=(113, 113, 122), font=desc_font)
            else:
                # Leaf notes: White outline box with text wrapping
                draw.rectangle([x, y, x + 230, y + 70], fill=(255, 255, 255), outline=(228, 228, 231))
                draw.text((x + 10, y + 8), label[:35], fill=(24, 24, 27), font=title_font)
                if desc:
                    words = desc.split()
                    lines = []
                    current_line = ""
                    for word in words:
                        if len(current_line + " " + word) < 45:
                            current_line = current_line + " " + word if current_line else word
                        else:
                            lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    
                    dy = 24
                    for line in lines[:3]:
                        draw.text((x + 10, y + dy), line, fill=(113, 113, 122), font=desc_font)
                        dy += 13

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

study_tool_service = StudyToolService()


