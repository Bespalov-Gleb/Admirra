from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from core.database import get_db
from core import models, schemas, security
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.Token)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with email, optional username, and password.
    """
    import logging
    logger = logging.getLogger("api")
    
    try:
        logger.info(f"Registration attempt for email: {user.email}, username: {user.username}")
        
        # Check email uniqueness
        db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user_email:
            logger.warning(f"Registration failed: Email {user.email} already registered")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check username uniqueness if provided
        if user.username:
            db_user_name = db.query(models.User).filter(models.User.username == user.username).first()
            if db_user_name:
                logger.warning(f"Registration failed: Username {user.username} already taken")
                raise HTTPException(status_code=400, detail="Username already taken")
        
        hashed_password = security.get_password_hash(user.password)
        new_user = models.User(
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            password_hash=hashed_password,
            role=models.UserRole.MANAGER
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User registered successfully: {user.email} (ID: {new_user.id})")
        
        # Auto-login after registration
        access_token = security.create_access_token(
            data={"sub": new_user.email}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error for {user.email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    login_data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login using email. Accepts JSON data.
    """
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    
    if not user or not security.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token = security.create_access_token(
        data={"sub": user.email}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """
    Get current logged in user details.
    """
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
def update_users_me(
    updates: schemas.UserUpdateSettings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Update current logged in user settings (safe subset of fields).
    """
    # Обновляем только разрешённые поля
    if updates.username is not None:
        # Проверяем уникальность username
        existing = db.query(models.User).filter(
            models.User.username == updates.username,
            models.User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = updates.username

    if updates.first_name is not None:
        current_user.first_name = updates.first_name

    if updates.last_name is not None:
        current_user.last_name = updates.last_name

    if updates.yandex_finance_token is not None:
        current_user.yandex_finance_token = updates.yandex_finance_token

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
