from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUDIENCE = f"https://{AUTH0_DOMAIN}/api/v2/"

app = FastAPI()


async def get_auth_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "audience": AUDIENCE,
                "grant_type": "client_credentials"
            }
        )
        response.raise_for_status()
        return response.json()["access_token"]


@app.post("/auth0-management")
async def auth0_management(request: Request):
    body = await request.json()
    action = body.get("action")
    parameters = body.get("parameters", {})

    try:
        token = await get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            if action == "getUsers":
                r = await client.get(f"https://{AUTH0_DOMAIN}/api/v2/users", headers=headers)
            elif action == "getUserById":
                user_id = parameters.get("user_id")
                r = await client.get(f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}", headers=headers)
            else:
                return JSONResponse(status_code=400, content={"error": "Unsupported action"})

        r.raise_for_status()
        return r.json()

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
