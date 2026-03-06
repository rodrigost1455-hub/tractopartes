from fastapi import APIRouter, HTTPException, Depends
from app.core.security import authenticate_user, create_access_token, get_current_user
from app.schemas.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    user = authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token({"sub": user["username"], "rol": user["rol"]})
    return TokenResponse(access_token=token)


@router.get("/me")
def me(user = Depends(get_current_user)):
    return {"username": user["username"], "rol": user["rol"]}
