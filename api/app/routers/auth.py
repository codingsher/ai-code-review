"""GitHub OAuth flow -> platform JWTs."""
import httpx
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token

router = APIRouter()

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_USER = "https://api.github.com/user"


@router.get("/github/login")
def github_login():
    url = (
        f"{GITHUB_AUTHORIZE}?client_id={settings.github_client_id}"
        "&scope=read:user,repo"
    )
    return {"authorize_url": url}


@router.get("/github/callback")
async def github_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        gh_token = token_data.get("access_token")
        if not gh_token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "OAuth exchange failed")

        user_resp = await client.get(
            GITHUB_USER, headers={"Authorization": f"Bearer {gh_token}"}
        )
        gh_user = user_resp.json()

    # TODO Phase 3: upsert user in Postgres, store encrypted gh_token
    user_id = str(gh_user["id"])
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "user": {"id": user_id, "login": gh_user["login"], "avatar": gh_user["avatar_url"]},
    }
