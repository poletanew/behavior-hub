import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.room import RoomCreateRequest, RoomResponse
from app.services import room_service

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomResponse])
def list_rooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Addendum v3.0, RF-26 — salas de atendimento da clínica/conta individual."""
    return room_service.list_rooms(db, user)


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return room_service.create_room(db, user, payload)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room_service.delete_room(db, user, room_id)
