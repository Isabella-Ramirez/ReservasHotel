from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rbac import TokenResponse
from app.models.user import User, UserLogin, UserResponse
from app.tools.auth import (
    create_access_token,
    get_current_user,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Validar credenciales y devolver un token JWT."""

    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )

    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo"
        )

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def read_current_user(request: Request, db: Session = Depends(get_db)) -> UserResponse:
    """Obtener los datos del usuario autenticado."""
    
    current_user = get_current_user(request, db)
    return current_user
