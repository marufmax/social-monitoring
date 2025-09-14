# app/auth/auth.py
from fastapi import APIRouter, Request, Response, HTTPException
from supertokens_python.recipe.emailpassword import API as ep_api
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer

router = APIRouter(prefix="/auth")


@router.post("/signup")
async def signup(request: Request, response: Response):
    body = await request.json()
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    result = await ep_api.sign_up(email=email, password=password)
    if result.status == "OK":
        # Automatically create session after signup
        session = await SessionContainer.create_new_session(user_id=result.user.user_id)
        session.add_to_response(response)
        return {"status": "OK", "user_id": result.user.user_id}
    else:
        raise HTTPException(status_code=400, detail=result.message)


@router.post("/login")
async def login(request: Request, response: Response):
    body = await request.json()
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    result = await ep_api.sign_in(email=email, password=password)
    if result.status == "OK":
        # Create session
        session = await SessionContainer.create_new_session(user_id=result.user.user_id)
        session.add_to_response(response)
        return {"status": "OK", "user_id": result.user.user_id}
    else:
        raise HTTPException(status_code=401, detail=result.message)


@router.post("/logout")
async def logout(session: SessionContainer = verify_session()):
    await session.revoke_session()
    return {"status": "OK", "message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(session: SessionContainer = verify_session()):
    return {
        "user_id": session.get_user_id(),
        "session_handle": session.get_handle()
    }
