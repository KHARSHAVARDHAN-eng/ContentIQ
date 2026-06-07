from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.users import get_current_user
from app.models.user import User
from app.models.rag_evaluation import RAGEvaluation
from app.schemas.rag_evaluation import FeedbackRequest, EvaluationLogResponse, EvaluationStatsResponse
from app.services.eval_service import eval_service

router = APIRouter()

@router.get("/logs", response_model=List[EvaluationLogResponse])
def get_evaluation_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        logs = eval_service.get_user_logs(db, current_user.id)
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch logs: {str(e)}"
        )

@router.get("/stats", response_model=EvaluationStatsResponse)
def get_evaluation_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        stats = eval_service.get_aggregate_stats(db, current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile statistics: {str(str(e))}"
        )

@router.post("/{eval_id}/feedback", response_model=EvaluationLogResponse)
def submit_feedback(
    eval_id: int,
    feedback_req: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    eval_entry = db.query(RAGEvaluation).filter(
        RAGEvaluation.id == eval_id,
        RAGEvaluation.user_id == current_user.id
    ).first()

    if not eval_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation log entry not found."
        )

    # Validate feedback range
    if feedback_req.feedback not in [1, -1, 0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback value. Must be 1, -1, or 0."
        )

    try:
        eval_entry.user_feedback = feedback_req.feedback
        db.commit()
        db.refresh(eval_entry)
        
        # Get matching document name to conform to schema response
        logs = eval_service.get_user_logs(db, current_user.id)
        matched_log = next((l for l in logs if l["id"] == eval_entry.id), None)
        if matched_log:
            return matched_log
        
        # Fallback if log query failed
        return eval_entry
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )
