"""Edge Agent authentication router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from pydantic import BaseModel

from ..db import get_db
from ..models import User
from ..auth import create_access_token

router = APIRouter(prefix="/edge", tags=["Edge Agent"])


class EdgeAuthRequest(BaseModel):
    agent_id: str
    secret: str


class EdgeAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth", response_model=EdgeAuthResponse)
async def authenticate_edge_agent(
    data: EdgeAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate an Edge Agent using agent_id and secret.
    
    For now, we use a simple secret-based auth. In production,
    this should use proper certificate-based authentication.
    """
    # Validate agent credentials
    # In a full implementation, we'd have an EdgeAgent model
    if not data.agent_id or not data.secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials"
        )
    
    # For demo, we create a token with edge_agent role
    # In production, this should verify against stored agent secrets
    access_token = create_access_token(
        data={
            "sub": f"edge_{data.agent_id}",
            "agent_id": data.agent_id,
            "type": "edge_agent"
        }
    )
    
    return EdgeAuthResponse(
        access_token=access_token,
        token_type="bearer"
    )
