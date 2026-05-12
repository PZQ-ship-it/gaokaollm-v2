from pydantic import BaseModel


class IcebergProfile(BaseModel):
    profile_id: str
    explicit_query: str
    hidden_bottom_line: str
    ground_truth_weights: dict[str, float]
