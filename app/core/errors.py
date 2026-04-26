from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy.exc import IntegrityError
from starlette import status


@dataclass
class ApiException(Exception):
    """базовая ошибка api"""

    status_code: int
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


class UnauthorizedError(ApiException):
    """ошибка авторизации"""

    def __init__(
        self,
        message: str = "неверные учетные данные или токен",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            status.HTTP_401_UNAUTHORIZED,
            "unauthorized",
            message,
            context or {},
        )


class ForbiddenError(ApiException):
    """ошибка доступа"""

    def __init__(
        self,
        message: str = "недостаточно прав",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(
            status.HTTP_403_FORBIDDEN, "forbidden", message, context or {}
        )


class NotFoundError(ApiException):
    """ошибка отсутствующего ресурса"""

    def __init__(
        self, code: str, message: str, context: dict[str, Any] | None = None
    ):
        super().__init__(
            status.HTTP_404_NOT_FOUND, code, message, context or {}
        )


class ConflictError(ApiException):
    """ошибка конфликта"""

    def __init__(
        self, code: str, message: str, context: dict[str, Any] | None = None
    ):
        super().__init__(
            status.HTTP_409_CONFLICT, code, message, context or {}
        )


class BadRequestError(ApiException):
    """ошибка запроса"""

    def __init__(
        self, code: str, message: str, context: dict[str, Any] | None = None
    ):
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY, code, message, context or {}
        )


def error_payload(
    code: str, message: str, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """собирает единый формат ошибки"""

    return jsonable_encoder(
        {
            "error": {
                "code": code,
                "message": message,
                "context": context or {},
            }
        }
    )


def add_exception_handlers(app: FastAPI) -> None:
    """регистрирует обработчики ошибок"""

    @app.exception_handler(ApiException)
    async def api_exception_handler(
        _: Request, exc: ApiException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.context),
            headers=(
                {"WWW-Authenticate": "Bearer"}
                if exc.status_code == status.HTTP_401_UNAUTHORIZED
                else None
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = []
        for error in exc.errors():
            fields.append(
                {
                    "field": ".".join(
                        str(part) for part in error.get("loc", [])
                    ),
                    "message": error.get("msg", "invalid value"),
                    "type": error.get("type", "validation_error"),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload(
                "validation_error",
                "входные данные не прошли валидацию",
                {"fields": fields},
            ),
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(_: Request, __: JWTError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_payload("unauthorized", "невалидный токен", {}),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(
        _: Request, exc: IntegrityError
    ) -> JSONResponse:
        message = str(exc.orig)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_payload(
                "integrity_conflict",
                "нарушено ограничение целостности данных",
                {"details": message},
            ),
        )
