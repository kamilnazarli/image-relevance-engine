from pydantic import BaseModel, Field

class ImageAnaylsisResult(BaseModel):
    subject: str
    category: str
    attributes: list[str]
    caption: str
    confidence: float = Field(ge=0, le=1.0)

class Post(BaseModel):
    title: str
    content: str
    target_subject: str