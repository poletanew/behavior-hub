import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.room import Room
from app.models.user import User
from app.schemas.room import RoomCreateRequest


def _tenant_scope_filter(user: User):
    if user.clinic_id is not None:
        return Room.clinic_id == user.clinic_id
    return Room.individual_owner_id == user.id


def list_rooms(db: Session, user: User) -> list[Room]:
    return db.query(Room).filter(_tenant_scope_filter(user)).order_by(Room.name).all()


def create_room(db: Session, user: User, payload: RoomCreateRequest) -> Room:
    room = Room(
        clinic_id=user.clinic_id,
        individual_owner_id=user.id if user.clinic_id is None else None,
        name=payload.name,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def get_room_or_404(db: Session, user: User, room_id: uuid.UUID) -> Room:
    room = db.query(Room).filter(Room.id == room_id, _tenant_scope_filter(user)).first()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


def delete_room(db: Session, user: User, room_id: uuid.UUID) -> None:
    room = get_room_or_404(db, user, room_id)
    in_use = (
        db.query(Appointment)
        .filter(
            Appointment.room_id == room.id,
            Appointment.deleted_at.is_(None),
            Appointment.status.in_((AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)),
        )
        .first()
    )
    if in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This room has upcoming appointments and cannot be removed",
        )
    db.delete(room)
    db.commit()
