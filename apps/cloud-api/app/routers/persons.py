"""Person router - CRUD operations for persons (face recognition)."""
from typing import List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Person, FaceEmbedding, Camera, User, AuditLog
from ..schemas import PersonResponse, PersonCreate, PersonUpdate, FaceEmbeddingResponse
from ..security import get_current_user

router = APIRouter(prefix="/persons", tags=["Persons"])


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    data: PersonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new person for face recognition.
    """
    person = Person(
        tenant_id=current_user.tenant_id,
        name=data.name,
        notes=data.notes,
        status="active"
    )
    db.add(person)
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PERSON_CREATED",
        resource="person",
        action_metadata={"person_name": data.name, "person_id": str(person.id)}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(person)
    
    return person


@router.get("", response_model=List[PersonResponse])
async def list_persons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """
    List all persons for the current tenant.
    """
    persons = db.query(Person).filter(
        Person.tenant_id == current_user.tenant_id
    ).offset(offset).limit(limit).all()
    
    return persons


@router.get("/stats")
async def get_person_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get person statistics.
    """
    from sqlalchemy import func
    
    total_persons = db.query(func.count(Person.id)).filter(
        Person.tenant_id == current_user.tenant_id,
        Person.status == "active"
    ).scalar()
    
    total_embeddings = db.query(func.count(FaceEmbedding.id)).join(Person).filter(
        Person.tenant_id == current_user.tenant_id
    ).scalar()
    
    return {
        "total_persons": total_persons,
        "total_embeddings": total_embeddings
    }


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific person by ID.
    """
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.tenant_id == current_user.tenant_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    return person


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: UUID,
    data: PersonUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a person.
    """
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.tenant_id == current_user.tenant_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    if data.name is not None:
        person.name = data.name
    
    if data.notes is not None:
        person.notes = data.notes
    
    if data.status is not None:
        person.status = data.status
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PERSON_UPDATED",
        resource="person",
        action_metadata={"person_name": person.name, "person_id": str(person.id)}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(person)
    
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a person and all their face embeddings.
    """
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.tenant_id == current_user.tenant_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PERSON_DELETED",
        resource="person",
        action_metadata={"person_name": person.name, "person_id": str(person.id)}
    )
    db.add(audit_log)
    
    db.delete(person)
    db.commit()
    
    return None


@router.post("/{person_id}/embeddings", status_code=status.HTTP_201_CREATED)
async def add_face_embedding(
    person_id: UUID,
    embedding_vector: str = Form(...),
    source_image: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a face embedding to a person.
    
    The embedding_vector should be a JSON string of the face encoding array.
    """
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.tenant_id == current_user.tenant_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    try:
        json.loads(embedding_vector)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid embedding vector format. Must be JSON array."
        )
    
    embedding = FaceEmbedding(
        person_id=person_id,
        embedding_vector=embedding_vector,
        source_image_path=source_image
    )
    db.add(embedding)
    
    audit_log = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="FACE_EMBEDDING_ADDED",
        resource="person",
        action_metadata={"person_name": person.name, "person_id": str(person.id)}
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(embedding)
    
    return {
        "id": str(embedding.id),
        "person_id": str(person_id),
        "message": "Face embedding added successfully"
    }


@router.get("/{person_id}/embeddings")
async def list_face_embeddings(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all face embeddings for a person.
    """
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.tenant_id == current_user.tenant_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.person_id == person_id
    ).all()
    
    return [
        {
            "id": str(e.id),
            "source_image_path": e.source_image_path,
            "created_at": e.created_at.isoformat()
        }
        for e in embeddings
    ]


@router.delete("/{person_id}/embeddings/{embedding_id}")
async def delete_face_embedding(
    person_id: UUID,
    embedding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a face embedding.
    """
    person = db.query(Person).filter(
        Person.id == person_id,
        Person.tenant_id == current_user.tenant_id
    ).first()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    embedding = db.query(FaceEmbedding).filter(
        FaceEmbedding.id == embedding_id,
        FaceEmbedding.person_id == person_id
    ).first()
    
    if not embedding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Embedding not found"
        )
    
    db.delete(embedding)
    db.commit()
    
    return {"message": "Embedding deleted successfully"}
