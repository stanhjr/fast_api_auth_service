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
from tools import get_url, HeadersService

app = FastAPI()
Instrumentator().instrument(app).expose(app)

CHAT_GPT_SERVER = AsyncClient()


async def _reverse_proxy(request: Request):
    headers = dict(request.headers).copy()
    headers_service = HeadersService(headers=headers)

    if not headers_service.is_valid():
        raise HTTPException(status_code=400, detail="Not device_id or auth_token")

    if not AuthService(
            device_id=headers_service.get_device_id(),
            auth_token=headers_service.get_auth_token()
    ).is_authenticate():
        raise HTTPException(status_code=401, detail="Unauthorized, token not valid")

    url = get_url(type_query=headers_service.get_type_query())
    headers = headers_service.get_modify_headers()
    rp_req = CHAT_GPT_SERVER.build_request(
        request.method, url, headers=headers, content=await request.body(), timeout=None
    )

    rp_resp = await CHAT_GPT_SERVER.send(rp_req, stream=True)

    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )
