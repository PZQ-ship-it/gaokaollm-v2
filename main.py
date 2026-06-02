import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.api.chat_api import router as chat_router  # noqa: E402


app = FastAPI(title="Gaokao Pareto Recommendation API")
app.include_router(chat_router)
WEB_INDEX = Path(__file__).resolve().parent / "app" / "web" / "index.html"
WEB_SHOWCASE = Path(__file__).resolve().parent / "app" / "web" / "ui_showcase.html"
WEB_DEMO = Path(__file__).resolve().parent / "app" / "web" / "demo.html"


def _html_file(path: Path) -> FileResponse:
    return FileResponse(
        path,
        headers={
            "Cache-Control": "no-store, max-age=0, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/ui", include_in_schema=False)
async def ui() -> FileResponse:
    return _html_file(WEB_DEMO)


@app.get("/ui-basic", include_in_schema=False)
async def ui_basic() -> FileResponse:
    return _html_file(WEB_INDEX)


@app.get("/ui-showcase", include_in_schema=False)
async def ui_showcase() -> FileResponse:
    return _html_file(WEB_SHOWCASE)


@app.get("/demo", include_in_schema=False)
async def demo() -> FileResponse:
    return _html_file(WEB_DEMO)
