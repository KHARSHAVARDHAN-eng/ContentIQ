from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import io
import zipfile
import tempfile
import os

from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.study_tool import FlashCardDeck, FlashCard, StudyPack
from app.schemas.study_tool import (
    FlashCardDeckResponse,
    FlashCardGenerateRequest,
    MCQRequest,
    MCQResponse,
    MindMapRequest,
    MindMapResponse,
    StudyPackRequest,
    StudyPackResponse
)
from app.services.study_tool_service import study_tool_service

router = APIRouter()

@router.post("/flashcards/generate", response_model=FlashCardDeckResponse, status_code=status.HTTP_201_CREATED)
def generate_deck(
    request: FlashCardGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve and verify document ownership
    doc = db.query(Document).filter(
        Document.id == request.document_id,
        Document.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )

    # Get document text
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc.id
    ).order_by(DocumentPage.page_number.asc()).all()

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected document has no extracted text content. Please wait for processing to finish."
        )

    full_text = "\n\n".join([page.extracted_text for page in pages])
    if not full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The document text content is empty."
        )

    # Call LLM generator service
    cards_data = study_tool_service.generate_flashcards(doc.name, full_text)
    if not cards_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate flashcards from document content. Please try again."
        )

    # Save deck and cards to db
    deck = FlashCardDeck(
        user_id=current_user.id,
        document_id=doc.id,
        title=f"Flashcards: {doc.name}"
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)

    for item in cards_data:
        card = FlashCard(
            deck_id=deck.id,
            question=item.get("question", "No Question"),
            answer=item.get("answer", "No Answer")
        )
        db.add(card)

    db.commit()
    db.refresh(deck)

    return deck

@router.get("/flashcards", response_model=List[FlashCardDeckResponse])
def get_user_decks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    decks = db.query(FlashCardDeck).filter(
        FlashCardDeck.user_id == current_user.id
    ).order_by(FlashCardDeck.created_at.desc()).all()
    return decks

@router.get("/flashcards/{deck_id}", response_model=FlashCardDeckResponse)
def get_deck_detail(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deck = db.query(FlashCardDeck).filter(
        FlashCardDeck.id == deck_id,
        FlashCardDeck.user_id == current_user.id
    ).first()

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard deck not found."
        )

    return deck

@router.delete("/flashcards/{deck_id}", status_code=status.HTTP_200_OK)
def delete_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deck = db.query(FlashCardDeck).filter(
        FlashCardDeck.id == deck_id,
        FlashCardDeck.user_id == current_user.id
    ).first()

    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard deck not found."
        )

    db.delete(deck)
    db.commit()

    return {"success": True, "message": "Flashcard deck deleted successfully."}

@router.post("/mcqs/generate", response_model=MCQResponse)
def generate_mcqs(
    request: MCQRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve and verify document ownership
    doc = db.query(Document).filter(
        Document.id == request.document_id,
        Document.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )

    # Get document text
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc.id
    ).order_by(DocumentPage.page_number.asc()).all()

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected document has no extracted text content. Please wait for processing to finish."
        )

    full_text = "\n\n".join([page.extracted_text for page in pages])
    if not full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The document text content is empty."
        )

    # Call LLM generator service
    mcqs_data = study_tool_service.generate_mcqs(
        document_name=doc.name,
        document_text=full_text,
        difficulty=request.difficulty,
        count=request.count or 5
    )

    if not mcqs_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate MCQs from document content. Please try again."
        )

    # Map option formatting if needed to guarantee clean response list
    formatted_mcqs = []
    for item in mcqs_data:
        formatted_mcqs.append({
            "question": item.get("question", "Question"),
            "options": item.get("options", []),
            "correct_answer": item.get("correct_answer", "A"),
            "explanation": item.get("explanation", "No explanation provided.")
        })

    return {"mcqs": formatted_mcqs}

@router.post("/mindmaps/generate", response_model=MindMapResponse)
def generate_mindmap_endpoint(
    request: MindMapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve and verify document ownership
    doc = db.query(Document).filter(
        Document.id == request.document_id,
        Document.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )

    # Get document text
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc.id
    ).order_by(DocumentPage.page_number.asc()).all()

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected document has no extracted text content. Please wait for processing to finish."
        )

    full_text = "\n\n".join([page.extracted_text for page in pages])
    if not full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The document text content is empty."
        )

    # Call LLM generator service
    mindmap_data = study_tool_service.generate_mindmap(
        document_name=doc.name,
        document_text=full_text
    )

    if not mindmap_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate mindmap from document content. Please try again."
        )

    return mindmap_data

# Helper function to generate PDF using reportlab
def build_pack_pdf(pack: StudyPack) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Parse JSON fields
    summary_data = json.loads(pack.summary)
    summary_text = summary_data.get("summary", "No summary available.")
    takeaways = summary_data.get("takeaways", [])
    
    cards = json.loads(pack.flashcards)
    mcqs = json.loads(pack.mcqs)
    mindmap = json.loads(pack.mindmap)

    # Output buffer
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=letter,
        leftMargin=54, rightMargin=54,
        topMargin=54, bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=32,
        leading=38,
        textColor=colors.HexColor('#18181b'),
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0ea5e9'),
        spaceAfter=30
    )
    
    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#71717a'),
        spaceAfter=4
    )

    h1_style = ParagraphStyle(
        'Heading1Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#18181b'),
        spaceAfter=15,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#18181b'),
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#27272a'),
        spaceAfter=10
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=5
    )

    flowables = []

    # --- PAGE 1: COVER PAGE ---
    flowables.append(Spacer(1, 150))
    flowables.append(Paragraph("DocumentIQ", meta_style))
    flowables.append(Paragraph("Learning Study Pack", title_style))
    flowables.append(Paragraph(pack.title, subtitle_style))
    flowables.append(Spacer(1, 100))
    flowables.append(Paragraph(f"Created: {pack.created_at.strftime('%Y-%m-%d %H:%M')}", meta_style))
    flowables.append(PageBreak())

    # --- PAGE 2: SUMMARY & TAKEAWAYS ---
    flowables.append(Paragraph("1. Executive Summary & Takeaways", h1_style))
    flowables.append(Paragraph(summary_text, body_style))
    flowables.append(Spacer(1, 15))
    
    if takeaways:
        flowables.append(Paragraph("Key Conceptual Takeaways", h2_style))
        for item in takeaways:
            flowables.append(Paragraph(f"• {item}", bullet_style))
            
    flowables.append(PageBreak())

    # --- PAGE 3: FLASHCARDS ---
    flowables.append(Paragraph("2. Active Recall Flashcards", h1_style))
    flowables.append(Paragraph("Review these core question and answer cards to test your knowledge retrieval.", body_style))
    flowables.append(Spacer(1, 10))
    
    for idx, card in enumerate(cards):
        q = card.get("question", "Question")
        a = card.get("answer", "Answer")
        card_data = [
            [Paragraph(f"<b>Card #{idx+1}</b>", body_style)],
            [Paragraph(f"<b>Q:</b> {q}", body_style)],
            [Paragraph(f"<b>A:</b> {a}", body_style)]
        ]
        t = Table(card_data, colWidths=[500])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f4f5')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e4e4e7')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        flowables.append(t)
        flowables.append(Spacer(1, 12))
        
    flowables.append(PageBreak())

    # --- PAGE 4: MCQ ASSESSMENT ---
    flowables.append(Paragraph("3. Multiple Choice Assessment", h1_style))
    flowables.append(Paragraph("Test your long-term retention. Try to solve these questions independently before reviewing the answer key.", body_style))
    flowables.append(Spacer(1, 10))
    
    for idx, q in enumerate(mcqs):
        q_text = q.get("question", "Question")
        options = q.get("options", [])
        
        q_block = [Paragraph(f"<b>Q{idx+1}. {q_text}</b>", body_style)]
        for opt in options:
            q_block.append(Paragraph(opt, bullet_style))
            
        flowables.append(KeepTogether(q_block + [Spacer(1, 15)]))
        
    flowables.append(PageBreak())

    # --- PAGE 5: ANSWER KEY ---
    flowables.append(Paragraph("4. Answer Key & Tutor Explanations", h1_style))
    flowables.append(Spacer(1, 10))
    
    for idx, q in enumerate(mcqs):
        correct = q.get("correct_answer", "")
        exp = q.get("explanation", "")
        ans_block = [
            Paragraph(f"<b>Question #{idx+1}</b>", h2_style),
            Paragraph(f"Correct Option: <b>{correct}</b>", body_style),
            Paragraph(f"<b>Explanation:</b> {exp}", body_style)
        ]
        flowables.append(KeepTogether(ans_block + [Spacer(1, 10)]))
        
    flowables.append(PageBreak())

    # --- PAGE 6: CONCEPT MAP ---
    flowables.append(Paragraph("5. Conceptual Mind Map Diagram", h1_style))
    flowables.append(Paragraph("Visualize the core semantic relationships and branch details of your document.", body_style))
    flowables.append(Spacer(1, 20))
    
    # Generate Mindmap PNG using PIL
    png_bytes = study_tool_service.draw_mindmap_png(mindmap)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(png_bytes)
        tmp_path = tmp.name

    try:
        from PIL import Image as PILImage
        with PILImage.open(tmp_path) as pimg:
            w, h = pimg.size
        
        pdf_width = 480
        scale = pdf_width / w
        render_w = pdf_width
        render_h = h * scale
        
        flowables.append(RLImage(tmp_path, width=render_w, height=render_h))
    except Exception as e:
        flowables.append(Paragraph(f"[Mindmap Image Generation Error: {e}]", body_style))
    
    # Build Document
    doc.build(flowables)
    
    # Clean up temp file
    try:
        os.remove(tmp_path)
    except OSError:
        pass
        
    return pdf_buffer.getvalue()

# Helper function to generate ZIP using reportlab PDFs
def build_pack_zip(pack: StudyPack) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Parse JSON fields
    summary_data = json.loads(pack.summary)
    summary_text = summary_data.get("summary", "No summary available.")
    takeaways = summary_data.get("takeaways", [])
    
    cards = json.loads(pack.flashcards)
    mcqs = json.loads(pack.mcqs)
    mindmap = json.loads(pack.mindmap)

    # Styles
    styles = getSampleStyleSheet()
    h1_style = ParagraphStyle(
        'H1', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#18181b'), spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#18181b'), spaceBefore=10, spaceAfter=5
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['BodyText'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#27272a'), spaceAfter=8
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=body_style, leftIndent=15, spaceAfter=4
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        
        # 1. Summary PDF
        summary_buf = io.BytesIO()
        s_doc = SimpleDocTemplate(summary_buf, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
        s_flowables = [
            Paragraph(f"Executive Summary: {pack.title}", h1_style),
            Paragraph(summary_text, body_style),
            Spacer(1, 15)
        ]
        if takeaways:
            s_flowables.append(Paragraph("Key takeaways", h2_style))
            for item in takeaways:
                s_flowables.append(Paragraph(f"• {item}", bullet_style))
        s_doc.build(s_flowables)
        zf.writestr("Summary.pdf", summary_buf.getvalue())

        # 2. Flashcards PDF
        fc_buf = io.BytesIO()
        fc_doc = SimpleDocTemplate(fc_buf, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
        fc_flowables = [
            Paragraph(f"Active Recall Flashcards: {pack.title}", h1_style),
            Spacer(1, 10)
        ]
        for idx, card in enumerate(cards):
            q = card.get("question", "Question")
            a = card.get("answer", "Answer")
            card_data = [
                [Paragraph(f"<b>Card #{idx+1}</b>", body_style)],
                [Paragraph(f"<b>Q:</b> {q}", body_style)],
                [Paragraph(f"<b>A:</b> {a}", body_style)]
            ]
            t = Table(card_data, colWidths=[500])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f4f4f5')),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e4e4e7')),
            ]))
            fc_flowables.append(t)
            fc_flowables.append(Spacer(1, 12))
        fc_doc.build(fc_flowables)
        zf.writestr("Flashcards.pdf", fc_buf.getvalue())

        # 3. MCQs PDF
        mcq_buf = io.BytesIO()
        mcq_doc = SimpleDocTemplate(mcq_buf, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
        mcq_flowables = [
            Paragraph(f"MCQ Assessment: {pack.title}", h1_style),
            Spacer(1, 10)
        ]
        for idx, q in enumerate(mcqs):
            q_text = q.get("question", "Question")
            options = q.get("options", [])
            q_block = [Paragraph(f"<b>Q{idx+1}. {q_text}</b>", body_style)]
            for opt in options:
                q_block.append(Paragraph(opt, bullet_style))
            mcq_flowables.append(KeepTogether(q_block + [Spacer(1, 12)]))
            
        mcq_flowables.append(PageBreak())
        mcq_flowables.append(Paragraph("Answer Key & Explanations", h1_style))
        for idx, q in enumerate(mcqs):
            correct = q.get("correct_answer", "")
            exp = q.get("explanation", "")
            ans_block = [
                Paragraph(f"<b>Question #{idx+1}</b>", h2_style),
                Paragraph(f"Correct Option: <b>{correct}</b>", body_style),
                Paragraph(f"<b>Explanation:</b> {exp}", body_style)
            ]
            mcq_flowables.append(KeepTogether(ans_block + [Spacer(1, 8)]))
        mcq_doc.build(mcq_flowables)
        zf.writestr("MCQs.pdf", mcq_buf.getvalue())

        # 4. MindMap PNG
        png_bytes = study_tool_service.draw_mindmap_png(mindmap)
        zf.writestr("MindMap.png", png_bytes)

    return zip_buffer.getvalue()

@router.post("/packs/generate", response_model=StudyPackResponse, status_code=status.HTTP_201_CREATED)
def generate_pack(
    request: StudyPackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    doc = db.query(Document).filter(
        Document.id == request.document_id,
        Document.user_id == current_user.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )

    # Get document text
    pages = db.query(DocumentPage).filter(
        DocumentPage.document_id == doc.id
    ).order_by(DocumentPage.page_number.asc()).all()

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected document has no extracted text content. Please wait for processing to finish."
        )

    full_text = "\n\n".join([page.extracted_text for page in pages])
    if not full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The document text content is empty."
        )

    # Check if a pack already exists to prevent duplicate LLM calls
    existing_pack = db.query(StudyPack).filter(
        StudyPack.document_id == doc.id,
        StudyPack.user_id == current_user.id
    ).first()

    if existing_pack:
        return existing_pack

    # Call LLM generation pipeline
    summary_data = study_tool_service.generate_summary(doc.name, full_text)
    cards_data = study_tool_service.generate_flashcards(doc.name, full_text)
    mcqs_data = study_tool_service.generate_mcqs(doc.name, full_text, "Medium", 5)
    mindmap_data = study_tool_service.generate_mindmap(doc.name, full_text)

    # Save to Database
    pack = StudyPack(
        user_id=current_user.id,
        document_id=doc.id,
        title=f"Study Pack: {doc.name}",
        summary=json.dumps(summary_data),
        flashcards=json.dumps(cards_data),
        mcqs=json.dumps(mcqs_data),
        mindmap=json.dumps(mindmap_data)
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)

    return pack

@router.get("/packs", response_model=List[StudyPackResponse])
def get_packs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(StudyPack).filter(StudyPack.user_id == current_user.id).order_by(StudyPack.created_at.desc()).all()

@router.get("/packs/{pack_id}/pdf")
def download_pack_pdf(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pack = db.query(StudyPack).filter(
        StudyPack.id == pack_id,
        StudyPack.user_id == current_user.id
    ).first()

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study Pack not found."
        )

    pdf_bytes = build_pack_pdf(pack)
    filename = f"{pack.title.replace(' ', '_')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/packs/{pack_id}/zip")
def download_pack_zip(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pack = db.query(StudyPack).filter(
        StudyPack.id == pack_id,
        StudyPack.user_id == current_user.id
    ).first()

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study Pack not found."
        )

    zip_bytes = build_pack_zip(pack)
    filename = f"{pack.title.replace(' ', '_')}.zip"
    
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

