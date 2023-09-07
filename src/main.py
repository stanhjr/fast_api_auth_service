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
from schemas.statistics import StatisticsData
from services.redis_service import RedisService
from services.user_statistics import UserStatisticService

from tools import HeadersService, get_url, get_num_tokens_from_list

app = FastAPI()
Instrumentator().instrument(app).expose(app)
CHAT_GPT_SERVER = AsyncClient()


@app.post("/api/proxy/")
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
    redis_service = RedisService()
    await redis_service.limit_tokens_exceeded_validation(device_id=headers_service.get_device_id(),
                                                         app_name=headers_service.get_app_name(),
                                                         type_model=headers_service.get_type_model())
    valid_api_key = await redis_service.get_valid_api_key()
    headers_service.set_api_key(valid_api_key=valid_api_key)
    headers = headers_service.get_modify_headers()
    rp_req = CHAT_GPT_SERVER.build_request(
        request.method, url, headers=headers, content=await request.body(), timeout=None
    )
    rp_resp = await CHAT_GPT_SERVER.send(rp_req, stream=True)

    if rp_resp.status_code == 401:
        await redis_service.set_expired_api_key(expired_api_key=headers_service.valid_api_key)

    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


@app.post("/api/statistics_data/chat/")
async def add_statistics_chat(
        request: Request,
        data: StatisticsData,
) -> dict[str, str | int]:
    headers = dict(request.headers).copy()
    headers_service = HeadersService(headers=headers)
    if not headers_service.is_valid_statistics():
        raise HTTPException(status_code=400, detail="Not device_id or auth_token")
    if not AuthService(
            device_id=headers_service.get_device_id(),
            auth_token=headers_service.get_auth_token()
    ).is_authenticate():
        raise HTTPException(status_code=401, detail="Unauthorized, token not valid")
    word_list = data.word_list
    tokens = get_num_tokens_from_list(word_list=word_list)
    statistics_service = UserStatisticService()
    await statistics_service.add_outgoing(
        device_id=data.device_id,
        app_name=data.app_name,
        tokens=tokens,
        type_query=data.type_model
    )

    return {
        "tokens": tokens,
        "device_id": data.device_id,
        "type_model": data.type_model
    }
