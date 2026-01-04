"""Onboarding API server with authentication and registration endpoints.

This server provides endpoints for:
- User signup and login
- Email verification
- Desktop app download tracking
- Chrome extension registration
- Sync status monitoring
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.auth import UserManager, User
from src.onboarding import OnboardingManager, OnboardingStep


# Initialize managers
user_manager = UserManager()
onboarding_manager = OnboardingManager()

# Create FastAPI app
app = FastAPI(
    title="Unified AI System - Onboarding API",
    description="User onboarding and device registration API",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class SignupRequest(BaseModel):
    """User signup request."""
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response with token."""
    token: str
    user: dict
    onboarding: dict


class DownloadRequest(BaseModel):
    """Desktop download request."""
    platform: str  # windows, macos, linux


class DeviceRegistration(BaseModel):
    """Desktop device registration."""
    device_name: str
    platform: str
    version: str


class ExtensionRegistration(BaseModel):
    """Browser extension registration."""
    version: str
    browser: str = "chrome"


class DeviceSettings(BaseModel):
    """Device settings update."""
    capture_enabled: Optional[bool] = None
    clipboard_enabled: Optional[bool] = None
    file_watcher_enabled: Optional[bool] = None


class ExtensionSettings(BaseModel):
    """Extension settings update."""
    history_enabled: Optional[bool] = None
    tabs_enabled: Optional[bool] = None
    bookmarks_enabled: Optional[bool] = None


# ============================================================================
# Authentication Helpers
# ============================================================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """Extract and validate user from authorization header.

    Args:
        authorization: Bearer token header

    Returns:
        Authenticated User

    Raises:
        HTTPException: If not authenticated
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    user = user_manager.validate_session(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


# ============================================================================
# Auth Endpoints
# ============================================================================

@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Register a new user account.

    Creates a user, session, and initializes onboarding state.
    """
    try:
        # Create user
        user = user_manager.create_user(
            email=request.email,
            name=request.name,
            password=request.password,
        )

        # Create session
        session = user_manager.create_session(user.id)

        # Initialize onboarding
        onboarding = onboarding_manager.create_onboarding(user.id)

        return AuthResponse(
            token=session.token,
            user=user.to_dict(),
            onboarding=onboarding.to_dict(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Authenticate an existing user."""
    user = user_manager.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create session
    session = user_manager.create_session(user.id)

    # Get onboarding state
    onboarding = onboarding_manager.get_onboarding_state(user.id)

    return AuthResponse(
        token=session.token,
        user=user.to_dict(),
        onboarding=onboarding.to_dict(),
    )


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate session."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        user_manager.invalidate_session(token)
    return {"message": "Logged out"}


@app.get("/api/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    onboarding = onboarding_manager.get_onboarding_state(user.id)
    return {
        "user": user.to_dict(),
        "onboarding": onboarding.to_dict(),
    }


@app.get("/api/auth/verify/{token}")
async def verify_email(token: str):
    """Verify email address using token."""
    if user_manager.verify_email(token):
        # Get user by token and update onboarding
        # Note: We need to find the user first
        return {"message": "Email verified successfully"}
    raise HTTPException(status_code=400, detail="Invalid or expired token")


# ============================================================================
# Onboarding Endpoints
# ============================================================================

@app.get("/api/onboarding/state")
async def get_onboarding_state(user: User = Depends(get_current_user)):
    """Get current onboarding state."""
    state = onboarding_manager.get_onboarding_state(user.id)
    return state.to_dict()


@app.get("/api/onboarding/sync")
async def get_sync_status(user: User = Depends(get_current_user)):
    """Get detailed sync status for all data sources."""
    return onboarding_manager.get_sync_summary(user.id)


# ============================================================================
# Desktop App Endpoints
# ============================================================================

@app.post("/api/desktop/download-token")
async def create_download_token(
    request: DownloadRequest,
    user: User = Depends(get_current_user)
):
    """Create a download token for tracking desktop app downloads."""
    if request.platform not in ["windows", "macos", "linux"]:
        raise HTTPException(status_code=400, detail="Invalid platform")

    token = onboarding_manager.create_download_token(user.id, request.platform)

    # Build download URL based on platform
    download_urls = {
        "windows": f"/api/desktop/download/{token}/unified-ai-setup.exe",
        "macos": f"/api/desktop/download/{token}/UnifiedAI.dmg",
        "linux": f"/api/desktop/download/{token}/unified-ai.AppImage",
    }

    return {
        "token": token,
        "download_url": download_urls[request.platform],
        "platform": request.platform,
    }


@app.get("/api/desktop/download/{token}/{filename}")
async def download_desktop_app(token: str, filename: str):
    """Download desktop app and track the download.

    In production, this would serve the actual installer.
    For now, it validates the token and returns a placeholder.
    """
    token_info = onboarding_manager.validate_download_token(token)

    if not token_info:
        raise HTTPException(status_code=400, detail="Invalid or expired download token")

    # In production, serve the actual file based on platform
    # For now, redirect to a placeholder or return info
    return {
        "message": "Download started",
        "platform": token_info["platform"],
        "next_step": "Install the app and sign in with your account",
    }


@app.post("/api/desktop/register")
async def register_device(
    request: DeviceRegistration,
    user: User = Depends(get_current_user)
):
    """Register a new desktop device after installation."""
    device = onboarding_manager.register_device(
        user_id=user.id,
        device_name=request.device_name,
        platform=request.platform,
        version=request.version,
    )
    return device.to_dict()


@app.post("/api/desktop/heartbeat/{device_id}")
async def device_heartbeat(device_id: str):
    """Update device heartbeat (called periodically by desktop app)."""
    if onboarding_manager.update_device_heartbeat(device_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Device not found")


@app.patch("/api/desktop/{device_id}/settings")
async def update_device_settings(
    device_id: str,
    settings: DeviceSettings,
    user: User = Depends(get_current_user)
):
    """Update device capture settings."""
    success = onboarding_manager.update_device_settings(
        device_id=device_id,
        capture_enabled=settings.capture_enabled,
        clipboard_enabled=settings.clipboard_enabled,
        file_watcher_enabled=settings.file_watcher_enabled,
    )
    if success:
        return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Device not found")


# ============================================================================
# Chrome Extension Endpoints
# ============================================================================

@app.get("/api/extension/install-url")
async def get_extension_install_url(user: User = Depends(get_current_user)):
    """Get Chrome Web Store installation URL."""
    # In production, this would be the actual Chrome Web Store URL
    return {
        "chrome": "https://chrome.google.com/webstore/detail/unified-ai/placeholder",
        "firefox": "https://addons.mozilla.org/en-US/firefox/addon/unified-ai/",
        "edge": "https://microsoftedge.microsoft.com/addons/detail/unified-ai/placeholder",
    }


@app.post("/api/extension/register")
async def register_extension(
    request: ExtensionRegistration,
    user: User = Depends(get_current_user)
):
    """Register a new browser extension after installation."""
    extension = onboarding_manager.register_extension(
        user_id=user.id,
        version=request.version,
        browser=request.browser,
    )
    return extension.to_dict()


@app.post("/api/extension/heartbeat/{extension_id}")
async def extension_heartbeat(extension_id: str):
    """Update extension heartbeat (called periodically by extension)."""
    if onboarding_manager.update_extension_heartbeat(extension_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Extension not found")


@app.patch("/api/extension/{extension_id}/settings")
async def update_extension_settings(
    extension_id: str,
    settings: ExtensionSettings,
    user: User = Depends(get_current_user)
):
    """Update extension capture settings."""
    success = onboarding_manager.update_extension_settings(
        extension_id=extension_id,
        history_enabled=settings.history_enabled,
        tabs_enabled=settings.tabs_enabled,
        bookmarks_enabled=settings.bookmarks_enabled,
    )
    if success:
        return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Extension not found")


# ============================================================================
# Onboarding UI
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_onboarding_ui():
    """Serve the onboarding web interface."""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    return HTMLResponse(content="<h1>Onboarding UI</h1><p>index.html not found</p>")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the onboarding server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()
