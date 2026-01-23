from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    agree: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool = True
    is_superuser: bool = True

@router.post("/auth/login")
async def login(user: UserLogin):
    """
    Stub login for demo
    """
    return {
        "access_token": "demo-token-12345",
        "token_type": "bearer"
    }

@router.post("/auth/register")
async def register(user: UserRegister):
    """
    Stub registration for demo
    """
    # Just echo success
    return {
        "access_token": "demo-token-12345",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "email": user.email,
            "username": user.username,
            "is_active": True
        }
    }

@router.get("/auth/me")
async def read_users_me():
    """
    Stub user info for demo
    """
    return {
        "id": 1,
        "email": "demo@example.com",
        "username": "DemoUser",
        "is_active": True,
        "is_superuser": True
    }
