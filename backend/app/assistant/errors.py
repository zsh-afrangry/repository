"""The main app and the narrow service share the same failure contract."""
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm.exc import StaleDataError
from app.business_errors import BusinessError


def install_errors(app):
    @app.exception_handler(BusinessError)
    async def business_error(_request, error):
        return JSONResponse(status_code=error.status, content={"detail": {"code": error.code, "message": str(error)}})

    @app.exception_handler(StaleDataError)
    async def stale_error(_request, _error):
        return JSONResponse(status_code=409, content={"detail": {"code": "version_conflict", "message": "记录已更新，请刷新后重试"}})

    @app.exception_handler(ValidationError)
    async def merged_validation_error(_request, _error):
        return JSONResponse(status_code=422, content={"detail": {"code": "invalid_fields", "message": "字段不符合业务契约，请检查日期、时刻或必填项"}})
