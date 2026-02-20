from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import schemas, models, database, auth

router = APIRouter(tags=["Authentication"])

@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        preferred_language=user.preferred_language
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(response: Response, request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Record Session
    user_session = models.UserSession(
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(user_session)
    db.commit()

    access_token = auth.create_access_token(data={"sub": user.email})
    
    # Set Cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.put("/users/me/language")
async def update_language(language_update: schemas.LanguageUpdate, user: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user.preferred_language = language_update.preferred_language
    db.commit()
    return {"message": "Language updated successfully", "language": user.preferred_language}

from fastapi.responses import RedirectResponse

@router.post("/logout")
async def logout(response: Response):
    """Clears the httponly access_token cookie and redirects to login."""
    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie(key="access_token", path="/")
    return redirect
