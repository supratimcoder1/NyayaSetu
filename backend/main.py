from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import uvicorn
from . import models, database, auth
from .routers import auth as auth_router
from .routers import chat as chat_router
from .routers import judicial as judicial_router
from .routers import pages as pages_router
from .routers import tools as tools_router

# Create Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="NyayaSetu")

# --- Middlewares ---
@app.middleware("http")
async def sliding_session_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Never interfere with the logout endpoint — it intentionally clears the cookie
    if request.url.path == "/logout":
        return response
    
    # Check for access token
    token = request.cookies.get("access_token")
    if token:
        try:
            # Decode simply to check validity (auth module has the key)
            payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username = payload.get("sub")
            
            if username:
                # Issue a FRESH token with reset timer (now + 30m)
                access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = auth.create_access_token(
                    data={"sub": username}, expires_delta=access_token_expires
                )
                
                # Update Cookie silently
                try:
                     response.set_cookie(
                        key="access_token",
                        value=access_token,
                        httponly=True,
                        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                        expires=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    )
                except:
                    pass
        except Exception:
            pass
            
    return response

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(judicial_router.router)
app.include_router(judicial_router.router_aux) # specific endpoint group
app.include_router(tools_router.router)
app.include_router(pages_router.router)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
