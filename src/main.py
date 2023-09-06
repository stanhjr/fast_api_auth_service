from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import JSONResponse

from auth.services import AuthService
from schemas.headers import TypeQueryEnum
from services.redis_service import RedisService
from services.user_statistics import UserStatisticService
from tools import (
    HeadersService,
    get_response,
    get_url,
)

app = FastAPI()
Instrumentator().instrument(app).expose(app)


async def _reverse_proxy(
        request: Request
):
    headers = dict(request.headers).copy()

    headers_service = HeadersService(headers=headers)
    if not headers_service.is_valid():
        raise HTTPException(status_code=400, detail="Not device_id or auth_token")

    if not AuthService(
            device_id=headers_service.get_device_id(),
            auth_token=headers_service.get_auth_token()
    ).is_authenticate():
        pass
        # raise HTTPException(status_code=401, detail="Unauthorized, token not valid")

    redis_service = RedisService()
    await redis_service.limit_tokens_exceeded_validation(device_id=headers_service.get_device_id(),
                                                         app_name=headers_service.get_app_name(),
                                                         type_model=headers_service.get_type_model())

    statistics_service = UserStatisticService()

    url = get_url(type_query=headers_service.get_type_query())
    response = await get_response(
        url,
        content=await request.body(),
        headers_service=headers_service,
        redis_service=redis_service
    )

    if response.status_code == 200 and response.content and headers_service.get_type_query() == TypeQueryEnum.chat:
        await statistics_service.add_outgoing(
            device_id=headers_service.get_device_id(),
            app_name=headers_service.get_app_name(),
            type_query=headers_service.get_type_query(),
            tokens=response.content["usage"]["total_tokens"]
        )
        await redis_service.set_tokens_by_device_id(device_id=headers_service.get_device_id(),
                                                    app_name=headers_service.get_app_name(),
                                                    tokens=int(response.content["usage"]["total_tokens"]),
                                                    )

    json_response = JSONResponse(response.content)
    json_response.status_code = response.status_code
    return json_response


app.add_route("/{path:path}", _reverse_proxy, ["GET", "POST"])
