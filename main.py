from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUDIENCE = f"https://{AUTH0_DOMAIN}/api/v2/"

app = FastAPI()

# アクションとエンドポイントの対応
ACTION_MAP = {
    "list_users": ("GET", "/api/v2/users"),
    "get_user": ("GET", "/api/v2/users/{user_id}"),
    "create_user": ("POST", "/api/v2/users"),
    "delete_user": ("DELETE", "/api/v2/users/{user_id}"),
    "update_user": ("PATCH", "/api/v2/users/{user_id}"),
    "get_user_logs": ("GET", "/api/v2/users/{user_id}/logs"),
    "list_connections": ("GET", "/api/v2/connections"),
    "create_connection": ("POST", "/api/v2/connections"),
    "delete_connection": ("DELETE", "/api/v2/connections/{id}"),
    "list_clients": ("GET", "/api/v2/clients"),
    "create_client": ("POST", "/api/v2/clients"),
    "delete_client": ("DELETE", "/api/v2/clients/{id}"),
    "list_roles": ("GET", "/api/v2/roles"),
    "create_role": ("POST", "/api/v2/roles"),
    "delete_role": ("DELETE", "/api/v2/roles/{id}"),
    "list_organizations": ("GET", "/api/v2/organizations"),
    "create_organization": ("POST", "/api/v2/organizations"),
    "delete_organization": ("DELETE", "/api/v2/organizations/{id}"),
    "list_log_streams": ("GET", "/api/v2/log-streams"),
    "create_log_stream": ("POST", "/api/v2/log-streams"),
    "delete_log_stream": ("DELETE", "/api/v2/log-streams/{id}"),
}


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

    print("=== Difyからのリクエスト ===")
    print(f"Action: {action}")
    print(f"Parameters: {parameters}")
    print("===========================")

    # パラメータが str の場合は辞書に変換
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except json.JSONDecodeError:
            return JSONResponse(status_code=400, content={"error": "Invalid parameters: not valid JSON string"})

    if action not in ACTION_MAP:
        print("[ERROR] Unsupported action")
        return JSONResponse(status_code=400, content={"error": "Unsupported action"})

    method, path_template = ACTION_MAP[action]

    # パスパラメータを埋め込み
    try:
        path = path_template.format(**parameters)
    except KeyError as e:
        print(f"[ERROR] Missing parameter for path: {e}")
        return JSONResponse(status_code=400, content={"error": f"Missing parameter: {e}"})
    except TypeError as e:
        print(f"[ERROR] Invalid format arguments: {e}")
        return JSONResponse(status_code=400, content={"error": f"Invalid parameter format: {e}"})

    # トークン取得
    token = await get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # クエリとボディの分離（Difyのリクエスト形式に対応）
    query_params = parameters.get("query", {})
    body_data = parameters.get("body", {}) if method in ["POST", "PATCH", "PUT"] else {}

    url = f"https://{AUTH0_DOMAIN}{path}"

    print("=== Auth0へのリクエスト ===")
    print(f"Method: {method}")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Query Params: {query_params}")
    print(f"Body: {body_data}")
    print("===========================")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=query_params,
                json=body_data if method in ["POST", "PATCH", "PUT"] else None
            )
            print("=== Auth0レスポンス ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            print("========================")
            response.raise_for_status()
            if response.status_code == 204:
                return {"message": "No Content: operation successful."}
            return response.json()

        except httpx.HTTPStatusError as e:
            print("=== Auth0 APIエラー ===")
            print(f"Status: {e.response.status_code}")
            print(f"Body: {e.response.text}")
            print("========================")
            return JSONResponse(status_code=e.response.status_code, content={"error": e.response.text})

        except Exception as e:
            print("=== 予期しないエラー ===")
            print(str(e))
            print("=======================")
            return JSONResponse(status_code=500, content={"error": str(e)})
