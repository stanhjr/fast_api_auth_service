import json
import os
import re
from io import BytesIO

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.responses import Response, StreamingResponse
from httpx import AsyncClient
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.background import BackgroundTask

from auth.services import AuthService
from schemas.headers import TypeQueryEnum
from schemas.statistics import StatisticsData
from services.redis_service import RedisService
from services.user_statistics import UserStatisticService
from tools import (
    HeadersService,
    get_num_tokens_from_list,
    get_url,
    num_tokens_from_string,
)

app = FastAPI()
Instrumentator().instrument(app).expose(app)
CHAT_GPT_SERVER = AsyncClient()


async def _reverse_proxy_deprecated(request: Request):
    headers = dict(request.headers).copy()
    headers_service = HeadersService(headers=headers)

    if not headers_service.is_old_valid():
        raise HTTPException(status_code=400, detail="Not device_id or auth_token")

    if not AuthService(
            device_id=headers_service.get_device_id(),
            auth_token=headers_service.get_auth_token()
    ).is_authenticate():
        raise HTTPException(status_code=401, detail="Unauthorized, token not valid")

    url = get_url(type_query=headers_service.get_type_query())
    headers = headers_service.get_modify_headers()
    headers["Authorization"] = f"Bearer {os.getenv('CHAT_GPT_TOKEN')}"
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


app.add_route("/{path:path}", _reverse_proxy_deprecated, ["GET", "POST"])


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
                                                         type_model=headers_service.get_type_model(),
                                                         type_query=headers_service.get_type_query())
    attempts_numbers = await redis_service.get_attempts_number()
    body = await request.body()
    for attempt in range(attempts_numbers):
        valid_api_key = await redis_service.get_valid_api_key()
        headers_service.set_api_key(valid_api_key=valid_api_key)
        headers = headers_service.get_modify_headers()
        rp_req = CHAT_GPT_SERVER.build_request(
            request.method, url, headers=headers, content=body, timeout=None
        )

        rp_resp = await CHAT_GPT_SERVER.send(rp_req, stream=True)
        if rp_resp.status_code == 401:
            await redis_service.set_expired_api_key(expired_api_key=headers_service.valid_api_key)
            continue

        if not headers_service.get_type_query() == TypeQueryEnum.chat:
            return StreamingResponse(
                rp_resp.aiter_raw(),
                status_code=rp_resp.status_code,
                headers=rp_resp.headers,
                background=BackgroundTask(rp_resp.aclose),
            )

        response_content = b""
        result_tokens = 0
        async for chunk in rp_resp.aiter_raw():
            response_content += chunk
            try:
                json_string = chunk.decode('utf-8')
                match = re.search(r'"content":"(.*?)"', json_string)
                if match:
                    content_string = match.group(1)
                    result_tokens += num_tokens_from_string(string=content_string)

            except Exception as e:
                print(e)

        statistics_service = UserStatisticService()
        await statistics_service.add_outgoing(
            device_id=headers_service.get_device_id(),
            app_name=headers_service.get_app_name(),
            tokens=result_tokens,
            type_query=headers_service.get_type_query(),
            chat_model=headers_service.get_type_model()
        )
        redis_service = RedisService()
        await redis_service.set_tokens_by_device_id(device_id=headers_service.get_device_id(),
                                                    app_name=headers_service.get_app_name(),
                                                    tokens=result_tokens,
                                                    type_model=headers_service.get_type_model(),
                                                    )

        return StreamingResponse(
            BytesIO(response_content),
            status_code=rp_resp.status_code,
            headers=rp_resp.headers,
            background=BackgroundTask(rp_resp.aclose),
        )
    return Response(json.dumps({"message": "all tokens expired"}), status_code=403)


@app.post("/api/statistics_data/chat/")
async def add_statistics_chat(
        request: Request,
        data: StatisticsData,
) -> dict[str, str | int]:
    headers = dict(request.headers).copy()
    headers_service = HeadersService(headers=headers)
    if not headers_service.is_valid_statistics():
        raise HTTPException(status_code=400, detail="Not auth_token")
    if not AuthService(
            device_id=headers_service.get_device_id(),
            auth_token=headers_service.get_auth_token()
    ).is_authenticate():
        raise HTTPException(status_code=401, detail="Unauthorized, token not valid")

    tokens = get_num_tokens_from_list(word_list=data.word_list)
    statistics_service = UserStatisticService()
    await statistics_service.add_outgoing(
        device_id=data.device_id,
        app_name=data.app_name,
        tokens=tokens,
        type_query=data.type_query,
        chat_model=data.chat_model
    )
    redis_service = RedisService()
    await redis_service.set_tokens_by_device_id(device_id=data.device_id,
                                                app_name=data.app_name,
                                                tokens=tokens,
                                                type_model=data.chat_model,
                                                )

    return {
        "tokens": tokens,
        "device_id": data.device_id,
        "type_model": data.chat_model
    }
