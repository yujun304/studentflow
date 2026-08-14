from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status: int, code: str, detail: str, fields: dict[str, Any] | None = None):
        self.status = status
        self.code = code
        self.detail = detail
        self.fields = fields


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"code": exc.code, "detail": exc.detail, "fields": exc.fields},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "detail": "입력값을 확인해 주세요.",
                "fields": exc.errors(),
            },
        )
