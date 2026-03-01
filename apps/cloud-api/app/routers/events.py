"""Event router - CRUD operations for events."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db import get_db
from ..models import Event, Camera, User, AuditLog
from ..schemas import EventResponse, EventCreate
from ..security import get_current_user

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new event (usually from Edge Agent).
    """
    camera = None
    if data.camera_id:
        camera = db.query(Camera).filter(
            Camera.id == data.camera_id,
            Camera.tenant_id == current_user.tenant_id
        ).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found"
            )

    event = Event(
        tenant_id=current_user.tenant_id,
        camera_id=data.camera_id,
        type=data.type,
        confidence=data.confidence,
        snapshot_path=data.snapshot_path,
        event_metadata=data.metadata
    )
    db.add(event)
    
    db.commit()
    db.refresh(event)
    
    return event


@router.get("", response_model=List[EventResponse])
async def list_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    camera_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
):
    """
    List events for the current tenant with pagination and filters.
    """
    query = db.query(Event).filter(
        Event.tenant_id == current_user.tenant_id
    )
    
    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    
    if event_type:
        query = query.filter(Event.type == event_type)
    
    events = query.order_by(desc(Event.created_at)).offset(offset).limit(limit).all()
    
    return events


@router.get("/stats")
async def get_event_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get event statistics for the current tenant.
    """
    from sqlalchemy import func
    
    total_events = db.query(func.count(Event.id)).filter(
        Event.tenant_id == current_user.tenant_id
    ).scalar()
    
    events_by_type = db.query(
        Event.type,
        func.count(Event.id)
    ).filter(
        Event.tenant_id == current_user.tenant_id
    ).group_by(Event.type).all()
    
    events_today = db.query(func.count(Event.id)).filter(
        Event.tenant_id == current_user.tenant_id,
        Event.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).scalar()
    
    return {
        "total_events": total_events,
        "events_today": events_today,
        "events_by_type": {event_type: count for event_type, count in events_by_type}
    }


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific event by ID.
    """
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.tenant_id == current_user.tenant_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an event.
    """
    event = db.query(Event).filter(
        Event.id == event_id,
        Event.tenant_id == current_user.tenant_id
    ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    db.delete(event)
    db.commit()
    
    return None
