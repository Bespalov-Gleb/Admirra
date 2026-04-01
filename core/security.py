from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core import models, schemas
from core.database import get_db
from core.config import get_config

# Configuration
cfg = get_config()
SECRET_KEY = cfg.security.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours
AUTH_REQUIRE_EMAIL_VERIFIED = cfg.auth.auth_require_email_verified

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Encryption for sensitive tokens
ENCRYPTION_KEY = cfg.security.encryption_key
from cryptography.fernet import Fernet

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_token(token: str) -> str:
    if not token: return None
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token_encrypted: str) -> str:
    if not token_encrypted: return None
    return fernet.decrypt(token_encrypted.encode()).decode()

bearer_scheme = HTTPBearer()

def get_current_user(auth: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = auth.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    if AUTH_REQUIRE_EMAIL_VERIFIED and not getattr(user, "email_verified", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return user
