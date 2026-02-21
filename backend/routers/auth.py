from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
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
        samesite="lax",
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

@router.post("/logout")
async def logout(response: Response):
    """Clears the httponly access_token cookie and redirects to login."""
    redirect = RedirectResponse(url="/login", status_code=303)
    redirect.delete_cookie(key="access_token", path="/")
    return redirect

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, current_admin: models.User = Depends(auth.get_current_user_from_cookie), db: Session = Depends(database.get_db)):
    """Admin endpoint to permanently delete a user and their associated data."""
    if not current_admin:
         raise HTTPException(status_code=401, detail="Not authenticated")
    if current_admin.role != "admin":
         raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")
    
    if current_admin.id == user_id:
         raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")
         
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_delete:
         raise HTTPException(status_code=404, detail="User not found")
         
    # SQLAlchemy relationships will handle cascading deletes if configured,
    # otherwise we might need to manually delete sessions/cases.
    # Our models are set to cascade="all, delete-orphan", so this is safe.
    db.delete(user_to_delete)
    db.commit()
    return {"message": f"User #{user_id} deleted successfully"}
