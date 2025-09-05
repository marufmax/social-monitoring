from pydantic import BaseModel, field_validator

class PostCreate(BaseModel):
    title: str
    content: str

    @field_validator("title")
    def title_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v
