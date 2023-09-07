import ast
import json
from io import BytesIO
import re

import brotli
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from httpx import AsyncClient

from prometheus_fastapi_instrumentator import Instrumentator
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from services.redis_service import RedisService

from tools import (
    HeadersService,
    get_stream_response,
    get_url, num_tokens_from_string, num_tokens_from_messages,
)

app = FastAPI()
Instrumentator().instrument(app).expose(app)


# async def _reverse_proxy(
#         request: Request
# ):
#     headers = dict(request.headers).copy()
#
#     headers_service = HeadersService(headers=headers)
#     if not headers_service.is_valid():
#         raise HTTPException(status_code=400, detail="Not device_id or auth_token")
#
#     # if not AuthService(
#     #         device_id=headers_service.get_device_id(),
#     #         auth_token=headers_service.get_auth_token()
#     # ).is_authenticate():
#     #     raise HTTPException(status_code=401, detail="Unauthorized, token not valid")
#
#     redis_service = RedisService()
#     await redis_service.limit_tokens_exceeded_validation(device_id=headers_service.get_device_id(),
#                                                          app_name=headers_service.get_app_name(),
#                                                          type_model=headers_service.get_type_model())
#
#     statistics_service = UserStatisticService()
#
#     url = get_url(type_query=headers_service.get_type_query())
#     response = await get_response(
#         url,
#         content=await request.body(),
#         headers_service=headers_service,
#         redis_service=redis_service
#     )
#
#     if response.status_code == 200 and response.content and headers_service.get_type_query() == TypeQueryEnum.chat:
#         await statistics_service.add_outgoing(
#             device_id=headers_service.get_device_id(),
#             app_name=headers_service.get_app_name(),
#             type_query=headers_service.get_type_query(),
#             tokens=response.content["usage"]["total_tokens"]
#         )
#         await redis_service.set_tokens_by_device_id(device_id=headers_service.get_device_id(),
#                                                     app_name=headers_service.get_app_name(),
#                                                     tokens=int(response.content["usage"]["total_tokens"]),
#                                                     )
#
#     json_response = JSONResponse(response.content)
#     json_response.status_code = response.status_code
#     return json_response


# app.add_route("/{path:path}", _reverse_proxy, ["GET", "POST"])


# async def _reverse_proxy_2(request: Request):
#     headers = dict(request.headers).copy()
#
#     headers_service = HeadersService(headers=headers)
#     url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
#     HTTP_SERVER = AsyncClient(base_url=get_url(type_query=headers_service.get_type_query()))
#     rp_req = HTTP_SERVER.build_request(
#         request.method, url, headers=headers_service.get_modify_headers(), content=await request.body()
#     )
#
#     rp_resp = await HTTP_SERVER.send(rp_req, stream=True)
#     response_content = b""
#     async for chunk in rp_resp.aiter_raw():
#         response_content += chunk
#
#     decoded_data = brotli.decompress(response_content)
#     data_dict = json.loads(decoded_data.decode('utf-8'))
#     print(data_dict, type(data_dict))
#
#     return StreamingResponse(
#         BytesIO(response_content),
#         status_code=rp_resp.status_code,
#         headers=rp_resp.headers,
#         background=BackgroundTask(rp_resp.aclose),
#     )
#
#
# app.add_route("/{path:path}", _reverse_proxy_2, ["GET", "POST"])

CHAT_GPT_SERVER = AsyncClient()


async def _reverse_proxy(request: Request):
    headers = dict(request.headers).copy()
    headers_service = HeadersService(headers=headers)
    if not headers_service.is_valid():
        raise HTTPException(status_code=400, detail="Not device_id or auth_token")
    # if not AuthService(
    #         device_id=headers_service.get_device_id(),
    #         auth_token=headers_service.get_auth_token()
    # ).is_authenticate():
    #     raise HTTPException(status_code=401, detail="Unauthorized, token not valid")
    redis_service = RedisService()
    await redis_service.limit_tokens_exceeded_validation(device_id=headers_service.get_device_id(),
                                                         app_name=headers_service.get_app_name(),
                                                         type_model=headers_service.get_type_model())
    url = get_url(type_query=headers_service.get_type_query())
    valid_api_key = await redis_service.get_valid_api_key()
    headers_service.set_api_key(valid_api_key=valid_api_key)
    headers = headers_service.get_modify_headers()
    rp_req = CHAT_GPT_SERVER.build_request(
        request.method, url, headers=headers, content=await request.body(), timeout=None
    )
    rp_resp = await CHAT_GPT_SERVER.send(rp_req, stream=True)
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
    print(result_tokens)
    d = {
        "device_id": "fdfdf",
        "app_name": "fdfdf",
        "word_list": ["I", "love", " you"]
    }
    if rp_resp.status_code == 401:
        await redis_service.set_expired_api_key(expired_api_key=headers_service.valid_api_key)

    return StreamingResponse(
        BytesIO(response_content),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )

app.add_route("/{path:path}", _reverse_proxy, ["GET", "POST"])