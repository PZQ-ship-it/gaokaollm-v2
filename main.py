import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.api.chat_api import router as chat_router  # noqa: E402


app = FastAPI(title="Gaokao Pareto Recommendation API")
app.include_router(chat_router)
WEB_INDEX = Path(__file__).resolve().parent / "app" / "web" / "index.html"
WEB_SHOWCASE = Path(__file__).resolve().parent / "app" / "web" / "ui_showcase.html"


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ui", include_in_schema=False)
async def ui() -> FileResponse:
    return FileResponse(WEB_INDEX)


@app.get("/ui-showcase", include_in_schema=False)
async def ui_showcase() -> FileResponse:
    return FileResponse(WEB_SHOWCASE)
