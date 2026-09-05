import os
import io
import traceback
import pdfplumber
from PIL import Image
from app.services.storage_service import storage_service
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.models.chunk_embedding import ChunkEmbedding
from app.core.config import settings
from app.services.embedding_service import embedding_service
from app.services.ocr_service import ocr_service
from app.services.adaptive_chunking import adaptive_chunker
from app.services.document_processor import process_document_task

def ocr_document_processor_task(document_id: int):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            print(f"Document {document_id} not found in database.")
            return

        # Download file bytes from storage_service
        try:
            file_bytes = storage_service.download_file(doc.path)
        except Exception as e:
            print(f"Error downloading file from storage for OCR: {e}")
            doc.status = "FAILED"
            db.commit()
            return

        _, ext = os.path.splitext(doc.name.lower())
        
        # Check if the document is directly an image or a PDF that might need OCR
        is_image = ext in [".png", ".jpg", ".jpeg"]
        is_pdf = ext == ".pdf"

        # Determine if we should perform OCR
        needs_ocr = False
        if is_image:
            needs_ocr = True
        elif is_pdf:
            # Inspect PDF text content and image layers to detect scanned documents
            total_text_length = 0
            has_scanned_images = False
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            total_text_length += len(page_text.strip())
                        if len(page.images) > 0:
                            has_scanned_images = True
            except Exception as pdf_err:
                print(f"Failed to pre-scan PDF text content: {pdf_err}")
                needs_ocr = True
            
            # If there is very little text or contains embedded scanned page images, trigger EasyOCR
            if total_text_length < 100 or has_scanned_images:
                needs_ocr = True
                print(f"PDF {doc.name} detected as scanned/image document (text_len: {total_text_length}, has_images: {has_scanned_images}). Routing to EasyOCR pipeline.")

        # If it doesn't need OCR, delegate directly to the locked production pipeline
        if not needs_ocr:
            print(f"Delegating document {document_id} to standard process_document_task...")
            db.close()
            process_document_task(document_id)
            return

        # Start OCR Ingestion Flow
        print(f"Starting OCR extraction pipeline for document {document_id}: {doc.name}")
        print("START parsing")
        doc.status = "OCR_PENDING"
        db.commit()

        # Clean up existing pages, chunks, and embeddings to prevent duplicates on rerun
        db.query(ChunkEmbedding).filter(
            ChunkEmbedding.chunk_id.in_(
                db.query(DocumentChunk.id).filter(DocumentChunk.document_id == document_id)
            )
        ).delete(synchronize_session=False)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
        db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete(synchronize_session=False)
        db.commit()

        doc.status = "OCR_PROCESSING"
        db.commit()

        pages_to_insert = []
        page_confidences = []

        if is_image:
            # Single page image processing
            try:
                with Image.open(io.BytesIO(file_bytes)) as img:
                    extracted_text, confidence = ocr_service.extract_text_from_image(img)
                    
                    db_page = DocumentPage(
                        document_id=doc.id,
                        page_number=1,
                        extracted_text=extracted_text or "[Empty Page]",
                        ocr_confidence=confidence
                    )
                    pages_to_insert.append(db_page)
                    page_confidences.append(confidence)
            except Exception as img_err:
                print(f"Failed to read/process image file: {img_err}")
                raise img_err

        elif is_pdf:
            # PDF rasterization and OCR processing page-by-page
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for idx, page in enumerate(pdf.pages):
                        # Convert PDF page to PIL Image using pdfplumber's PageImage original PIL property with higher resolution (150 DPI)
                        page_image = page.to_image(resolution=150)
                        pil_img = page_image.original

                        extracted_text, confidence = ocr_service.extract_text_from_image(pil_img)
                        
                        db_page = DocumentPage(
                            document_id=doc.id,
                            page_number=idx + 1,
                            extracted_text=extracted_text or "[Empty Page]",
                            ocr_confidence=confidence
                        )
                        pages_to_insert.append(db_page)
                        page_confidences.append(confidence)
            except Exception as pdf_err:
                print(f"Failed to process pages of PDF: {pdf_err}")
                raise pdf_err

        # Stage 1: Save extracted pages and transition status to OCR_COMPLETED
        if pages_to_insert:
            db.bulk_save_objects(pages_to_insert)
            
            # Save document-level average OCR confidence
            doc.ocr_confidence = float(sum(page_confidences) / len(page_confidences)) if page_confidences else 1.0
            doc.status = "OCR_COMPLETED"
            db.commit()
            print(f"Finished OCR extraction. Average confidence: {doc.ocr_confidence}. Transitioned to OCR_COMPLETED.")
            print("END parsing")

            # Stage 2: Transition to CHUNKED state and generate chunks
            doc.status = "CHUNKED"
            db.commit()
            print(f"Starting chunking for OCR document {document_id}...")
            print("START chunking")

            # Retrieve inserted pages from DB to get page numbers and contents
            pages_list = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number.asc()).all()

            # Run adaptive chunker once on full document text to obtain and save metadata parameters
            full_text = "\n\n".join([p.extracted_text for p in pages_list if p.extracted_text not in ["[Empty Page]", "[Empty Document]"]])
            _, metadata = adaptive_chunker.chunk_document(full_text, doc.name)
            
            doc.chunk_size = metadata["chunk_size"]
            doc.chunk_overlap = metadata["overlap"]
            doc.chunk_strategy = metadata["chunk_strategy"]
            doc.document_type = metadata["document_type"]
            doc.chunk_reason = metadata["chunk_reason"]
            db.commit()

            chunks_to_insert = []
            chunk_global_index = 0

            for page in pages_list:
                text = page.extracted_text
                if text in ["[Empty Page]", "[Empty Document]"]:
                    continue

                splits, _ = adaptive_chunker.chunk_document(text, doc.name)
                for split_text in splits:
                    clean_text = ocr_service.clean_ocr_text(split_text)
                    if not clean_text:
                        continue
                    db_chunk = DocumentChunk(
                        document_id=doc.id,
                        page_number=page.page_number,
                        chunk_index=chunk_global_index,
                        chunk_text=clean_text,
                        chunk_length=len(clean_text)
                    )
                    chunks_to_insert.append(db_chunk)
                    chunk_global_index += 1

            if chunks_to_insert:
                db.add_all(chunks_to_insert)
                db.flush()

                # Stage 3: Transition to EMBEDDING_GENERATION state
                doc.status = "EMBEDDING_GENERATION"
                db.commit()
                print(f"OCR Document {document_id} chunks created. Starting embedding generation...")
                print("END chunking")
                print("START embeddings")

                chunk_texts = [c.chunk_text for c in chunks_to_insert]
                vectors = embedding_service.get_embeddings(chunk_texts)

                embeddings_to_insert = []
                for chunk, vector in zip(chunks_to_insert, vectors):
                    db_emb = ChunkEmbedding(
                        chunk_id=chunk.id,
                        embedding_dimension=len(vector)
                    )
                    embeddings_to_insert.append(db_emb)

                if embeddings_to_insert:
                    db.add_all(embeddings_to_insert)

                # Stage 4: Transition to EMBEDDED
                doc.status = "EMBEDDED"
                db.commit()
                print(f"Finished embedding successfully. OCR Document {document_id} status: EMBEDDED")
                print("END embeddings")

                # Stage 5: Transition status to INDEXING
                doc.status = "INDEXING"
                db.commit()
                print(f"OCR Document {document_id}: Starting Qdrant indexing...")
                print("START indexing")

                from app.services.vector_store import vector_store
                vector_store.create_collection()
                vector_store.delete_document_vectors(doc.id)

                points_data = []
                for chunk, vector in zip(chunks_to_insert, vectors):
                    points_data.append({
                        "chunk_id": chunk.id,
                        "document_id": doc.id,
                        "document_name": doc.name,
                        "page_number": chunk.page_number,
                        "chunk_text": chunk.chunk_text,
                        "vector": vector
                    })

                if points_data:
                    vector_store.upsert_chunks_bulk(points_data)

                # Stage 6: Final transition to INDEXED
                print("START status update")
                doc.status = "INDEXED"
                db.commit()
                print("END status update")
                print(f"Finished OCR ingestion successfully. Document {document_id} status: INDEXED")
                print("END indexing")
                
                # Build Knowledge Graph if enabled
                if settings.GRAPHRAG_ENABLED:
                    print("START GraphRAG")
                    try:
                        from app.services.graph_builder import graph_builder
                        graph_builder.build_graph_for_document(doc.id, chunks_to_insert)
                        print("END GraphRAG")
                    except Exception as ge:
                        print(f"OCR Graph construction failed for document {document_id}: {ge}")
            else:
                print("START status update")
                doc.status = "INDEXED"
                db.commit()
                print("END status update")
                print(f"OCR Document {document_id} has no chunks. Transitioned to INDEXED")
        else:
            doc.status = "FAILED"
            db.commit()

    except Exception as e:
        print(f"Error during OCR extraction/chunking/embedding {document_id}: {e}")
        traceback.print_exc()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "FAILED"
                db.commit()
        except Exception as db_err:
            print(f"Failed to set document status to FAILED: {db_err}")
    finally:
        db.close()
