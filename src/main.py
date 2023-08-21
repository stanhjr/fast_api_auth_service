import os

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse
from httpx import AsyncClient
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.background import BackgroundTask

from auth.services import AuthService

app = FastAPI()
Instrumentator().instrument(app).expose(app)
BASE_URL = "https://api.openai.com/v1/chat/completions"
CHAT_GPT_SERVER = AsyncClient(base_url=BASE_URL)
CHAT_GPT_TOKEN = os.getenv("CHAT_GPT_TOKEN")


async def _reverse_proxy(request: Request):
    print(CHAT_GPT_TOKEN, "CHAT TOKEN")
    headers = dict(request.headers).copy()
    headers["host"] = "api.openai.com"
    device_id = headers.get("device-id")
    auth_token = headers.get("authorization")

    if not device_id or not auth_token:
        raise HTTPException(status_code=400, detail="Not device_id or auth_token")

    auth_service = AuthService(device_id=device_id, auth_token=auth_token)

    if not auth_service.is_authenticate():
        raise HTTPException(status_code=401, detail="Unauthorized, token not valid")

    headers.pop("device-id")
    headers.pop("authorization")
    headers["Authorization"] = f"Bearer {CHAT_GPT_TOKEN}"

    rp_req = CHAT_GPT_SERVER.build_request(
        request.method, BASE_URL, headers=headers, content=await request.body()
    )

    rp_resp = await CHAT_GPT_SERVER.send(rp_req, stream=True)

    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


app.add_route("/{path:path}", _reverse_proxy, ["GET", "POST"])
