from pydantic import BaseModel

class ImageAnaylsisResult(BaseModel):
    subject: str
    category: str
    attributes: list[str]
    caption: str
    confidence: float
