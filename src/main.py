import re

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
from schemas.headers import TypeQueryEnum
from services.redis_service import RedisService
from services.user_statistics import UserStatisticService
from tools import (
    HeadersService,
    get_url,
    num_tokens_from_string,
)

app = FastAPI()
Instrumentator().instrument(app).expose(app)
CHAT_GPT_SERVER = AsyncClient()


@app.post("/api/proxy/")
async def _reverse_proxy(request: Request):
    headers = dict(request.headers).copy()
    headers_service = HeadersService(headers=headers)
    print(1)
    if not headers_service.is_valid():
        raise HTTPException(status_code=401, detail={"message": "Not device_id or auth_token", "code": 0})
    # if not AuthService(
    #         device_id=headers_service.get_device_id(),
    #         auth_token=headers_service.get_auth_token()
    # ).is_authenticate():
    #     raise HTTPException(status_code=401, detail={"message": "Unauthorized, token not valid", "code": 1})
    url = get_url(type_query=headers_service.get_type_query())
    redis_service = RedisService()
    await redis_service.limit_tokens_exceeded_validation(device_id=headers_service.get_device_id(),
                                                         app_name=headers_service.get_app_name(),
                                                         type_model=headers_service.get_type_model(),
                                                         type_query=headers_service.get_type_query())
    bandl_id = headers_service.get_bandl_id()
    attempts_numbers = await redis_service.get_attempts_number(bandl_id=bandl_id)
    body = await request.body()
    for attempt in range(attempts_numbers):
        valid_api_key = await redis_service.get_valid_api_key(bandl_id=bandl_id)
        headers_service.set_api_key(valid_api_key=valid_api_key)
        headers = headers_service.get_modify_headers()
        rp_req = CHAT_GPT_SERVER.build_request(
            request.method, url, headers=headers, content=body, timeout=None
        )

        rp_resp = await CHAT_GPT_SERVER.send(rp_req, stream=True)
        if rp_resp.status_code == 401:
            await redis_service.set_expired_api_key(
                expired_api_key=headers_service.valid_api_key,
                app_name=headers_service.get_app_name(),
            )
            continue

        if not headers_service.get_type_query() == TypeQueryEnum.chat:
            return StreamingResponse(
                rp_resp.aiter_raw(),
                status_code=rp_resp.status_code,
                headers=rp_resp.headers,
                background=BackgroundTask(rp_resp.aclose),
            )

        async def generate():
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
                yield chunk
            statistics_service = UserStatisticService()
            await statistics_service.add_outgoing(
                device_id=headers_service.get_device_id(),
                app_name=headers_service.get_app_name(),
                tokens=result_tokens,
                type_query=headers_service.get_type_query(),
                chat_model=headers_service.get_type_model()
            )
            await redis_service.set_tokens_by_device_id(device_id=headers_service.get_device_id(),
                                                        app_name=headers_service.get_app_name(),
                                                        tokens=result_tokens,
                                                        type_model=headers_service.get_type_model(),
                                                        )

        return StreamingResponse(
            generate(),
            status_code=rp_resp.status_code,
            headers=rp_resp.headers,
            background=BackgroundTask(rp_resp.aclose),
        )
    raise HTTPException(status_code=403, detail={"message": "all tokens expired", "code": 9})
