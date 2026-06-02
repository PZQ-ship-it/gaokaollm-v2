from pydantic import BaseModel, Field


class UserConstraints(BaseModel):
    score: int = Field(..., ge=0, le=750)
    province: str
    major: str
    budget: int = Field(..., ge=0)
    selected_subjects: list[str] | None = None


class ChatRequest(BaseModel):
    thread_id: str
    message: str
    action: str | None = None
