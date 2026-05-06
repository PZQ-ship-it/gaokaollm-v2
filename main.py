from fastapi import FastAPI

from app.api.chat_api import router as chat_router


app = FastAPI(title="Gaokao Pareto Recommendation API")
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
