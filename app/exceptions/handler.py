from fastapi import Request
from fastapi.responses import JSONResponse


class ServiceException(Exception):
    def __init__(self, status_code: int, title: str, detail: str, instance: str = None):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.instance = instance


async def problem_details_handler(request: Request, exc: ServiceException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": exc.instance or str(request.url.path),
        },
        media_type="application/problem+json",
    )
