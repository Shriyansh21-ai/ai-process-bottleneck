from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

# TEMP user store (replace with DB later)
fake_users = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$W9yFZ3yZp0yLwJ6u8j4hOe9t6Vt8r2ZCqS7k0yWnQy6A8s4lXJjFa"
    }
}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}
