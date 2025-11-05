from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.guest import Guest
from app.models.rbac import Role, TokenResponse, TokenUserInfo
from app.models.user import User, UserLogin, UserRegistration, UserResponse
from app.tools.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.tools.error_handlers import (
    handle_database_errors,
    validate_resource_exists,
    validate_unique_field,
    get_custom_message,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@handle_database_errors
def register_user(payload: UserRegistration, db: Session = Depends(get_db)) -> TokenResponse:
    """Registrar un nuevo usuario con rol huésped y su ficha de huésped asociada."""

    validate_unique_field(
        db=db,
        model_class=User,
        field_name="email",
        field_value=payload.email,
        error_message=get_custom_message("User", "email_unique"),
    )

    guest_role = (
        db.query(Role)
        .filter(Role.code == "GUEST")
        .first()
    )
    guest_role = validate_resource_exists(guest_role, get_custom_message("Role", "not_found"))

    if payload.document_no:
        validate_unique_field(
            db=db,
            model_class=Guest,
            field_name="document_no",
            field_value=payload.document_no,
            error_message=get_custom_message("Guest", "document_unique"),
            include_deleted=True,
        )

    password_hash = get_password_hash(payload.password)
    
    full_name = f"{payload.first_name} {payload.last_name}"

    new_user = User(
        email=payload.email,
        password_hash=password_hash,
        full_name=full_name,
        role_id=guest_role.id,
        is_active=True,
    )

    db.add(new_user)
    db.flush()

    new_guest = Guest(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        birth_date=payload.birth_date,
        document_kind=payload.document_kind,
        document_no=payload.document_no,
        country=payload.country,
        city=payload.city,
        address_line=payload.address_line,
        user_id=new_user.id,
        created_by=new_user.id,
        updated_by=new_user.id,
    )

    db.add(new_guest)
    db.commit()

    access_token, expires_at = create_access_token(subject=str(new_user.id))
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=TokenUserInfo(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role_id=new_user.role_id,
            role_code=guest_role.code,
        ),
    )


@router.post("/login", response_model=TokenResponse)
@handle_database_errors
def login_user(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Validar credenciales y devolver un token JWT."""

    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_custom_message("User", "already_deleted"),
        )

    if user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo"
        )

    role = (
        db.query(Role)
        .filter(Role.id == user.role_id)
        .first()
    )
    role = validate_resource_exists(role, get_custom_message("Role", "not_found"))

    access_token, expires_at = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=TokenUserInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_id=user.role_id,
            role_code=role.code,
        ),
    )


@router.get("/me", response_model=UserResponse)
@handle_database_errors
def read_current_user(request: Request, db: Session = Depends(get_db)) -> UserResponse:
    """Obtener los datos del usuario autenticado."""

    current_user = get_current_user(request, db)

    if current_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_custom_message("User", "already_deleted"),
        )

    return current_user
