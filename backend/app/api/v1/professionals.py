from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(tags=["professionals"])


@router.get("/professionals", response_model=list[UserResponse])
def list_professionals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Lista os profissionais do mesmo tenant, usada para atribuicao de pacientes (Seção 7.3)."""
    if user.clinic_id is None:
        return [user]
    return db.query(User).filter(User.clinic_id == user.clinic_id).order_by(User.name).all()
