"""FastAPI router for Patient Health Assistant chatbot (/api/v1/chat)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, ChatConversation, ChatMessage, User
from app.schemas import (
    ChatConversationOut,
    ChatMessageOut,
    ChatMessageRequest,
    ChatResponse,
)
from app.services.chatbot import generate_chatbot_response

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chatbot"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def post_chat_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Main chatbot endpoint: process user health question and generate assistant response.

    Requires authentication. Automatically de-identifies user input and checks for emergency red-flag symptoms.
    """
    user_text = body.message.strip()
    if not user_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "EMPTY_MESSAGE", "message": "Message content cannot be empty", "details": {}}},
        )

    # 1. Get or create conversation
    conversation: Optional[ChatConversation] = None
    if body.conversation_id:
        result = await db.execute(
            select(ChatConversation)
            .options(selectinload(ChatConversation.messages))
            .where(ChatConversation.id == body.conversation_id, ChatConversation.user_id == current_user.id)
        )
        conversation = result.scalar_one_or_none()

    if conversation is None:
        title = user_text[:35] + "..." if len(user_text) > 35 else user_text
        conversation = ChatConversation(
            id=uuid.uuid4(),
            user_id=current_user.id,
            patient_id=body.patient_id,
            title=title,
        )
        db.add(conversation)
        await db.flush()

    # 2. Store user message in DB
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender="user",
        content=user_text,
    )
    db.add(user_msg)

    # Fetch recent conversation history explicitly via async query
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(desc(ChatMessage.created_at))
        .limit(6)
    )
    previous_messages = list(reversed(history_result.scalars().all()))
    history_dicts = [{"sender": m.sender, "content": m.content} for m in previous_messages]

    # Build patient dataset context if patient specified
    patient_ctx = None
    target_pt_id = body.patient_id or conversation.patient_id
    if target_pt_id:
        pt_res = await db.execute(select(Patient).where(Patient.id == target_pt_id))
        pt = pt_res.scalar_one_or_none()
        if pt:
            from app.models import DatasetRecord, PatientBaseline, RiskPrediction
            rec_res = await db.execute(
                select(DatasetRecord)
                .where(DatasetRecord.patient_code == pt.patient_code)
                .order_by(desc(DatasetRecord.recorded_at))
                .limit(1)
            )
            latest_rec = rec_res.scalar_one_or_none()

            base_res = await db.execute(
                select(PatientBaseline)
                .where(PatientBaseline.patient_id == pt.id)
                .order_by(desc(PatientBaseline.computed_at))
                .limit(1)
            )
            base = base_res.scalar_one_or_none()

            pred_res = await db.execute(
                select(RiskPrediction)
                .where(RiskPrediction.patient_id == pt.id)
                .order_by(desc(RiskPrediction.computed_at))
                .limit(1)
            )
            pred = pred_res.scalar_one_or_none()

            patient_ctx = {
                "patient_code": pt.patient_code,
                "display_name": pt.display_name,
                "risk_score": pt.current_risk_score,
                "risk_state": pt.current_risk_state.value if hasattr(pt.current_risk_state, "value") else str(pt.current_risk_state),
                "dataset_label": latest_rec.raw_label if latest_rec else None,
                "last_updated": pt.last_update.isoformat() if pt.last_update else None,
                "latest_vitals": {
                    "heart_rate": latest_rec.heart_rate if latest_rec else None,
                    "spo2": latest_rec.spo2 if latest_rec else None,
                    "respiratory_rate": latest_rec.respiratory_rate if latest_rec else None,
                    "systolic_bp": latest_rec.systolic_bp if latest_rec else None,
                    "diastolic_bp": latest_rec.diastolic_bp if latest_rec else None,
                    "temperature": latest_rec.temperature if latest_rec else None,
                } if latest_rec else None,
                "baseline": {
                    "hr_mean": base.hr_mean if base else None,
                    "spo2_mean": base.spo2_mean if base else None,
                    "rr_mean": base.rr_mean if base else None,
                } if base else None,
                "explanation": pred.explanation if pred else None,
            }

    # 3. Generate chatbot response
    bot_reply_text, is_emergency = await generate_chatbot_response(user_text, history_dicts, patient_ctx)

    # 4. Store assistant message in DB
    now = datetime.now(UTC)
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender="assistant",
        content=bot_reply_text,
    )
    db.add(assistant_msg)

    # Update conversation updated_at
    conversation.updated_at = now

    # Audit log entry
    db.add(
        AuditLog(
            id=uuid.uuid4(),
            user_id=current_user.id,
            action="chatbot.query",
            resource_type="chat_conversation",
            resource_id=str(conversation.id),
            details={"is_emergency": is_emergency},
        )
    )

    await db.commit()

    return ChatResponse(
        response=bot_reply_text,
        timestamp=now,
        conversation_id=conversation.id,
        emergency_warning=is_emergency,
        messages=[
            ChatMessageOut.model_validate(user_msg),
            ChatMessageOut.model_validate(assistant_msg),
        ],
    )


@router.get("/conversations", response_model=list[ChatConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat conversations for current user."""
    result = await db.execute(
        select(ChatConversation)
        .options(selectinload(ChatConversation.messages))
        .where(ChatConversation.user_id == current_user.id)
        .order_by(desc(ChatConversation.updated_at))
    )
    conversations = result.scalars().all()
    return [ChatConversationOut.model_validate(c) for c in conversations]


@router.post("/conversations", response_model=ChatConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    title: str = "New Health Assistant Chat",
    patient_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new empty conversation."""
    conv = ChatConversation(
        id=uuid.uuid4(),
        user_id=current_user.id,
        patient_id=patient_id,
        title=title,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ChatConversationOut.model_validate(conv)


@router.get("/conversations/{conversation_id}", response_model=ChatConversationOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific conversation history."""
    result = await db.execute(
        select(ChatConversation)
        .options(selectinload(ChatConversation.messages))
        .where(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "CONVERSATION_NOT_FOUND", "message": "Conversation not found", "details": {}}},
        )
    return ChatConversationOut.model_validate(conv)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation."""
    result = await db.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        await db.delete(conv)
        await db.commit()
