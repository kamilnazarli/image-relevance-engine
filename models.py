import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

from sqlalchemy import create_engine, text, inspect
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import ARRAY
from sqlalchemy import func
from sqlalchemy import ForeignKey
from sqlalchemy import Text
from sqlalchemy import String

from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

class Images(Base):
    __tablename__ = "images"

    id = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(String, unique=True)
    source_url: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class ImageMetadata(Base):
    __tablename__ = "image_metadata"

    id = mapped_column(Integer, primary_key=True)
    image_id = mapped_column(ForeignKey("images.id"), unique=True)
    subject: Mapped[str]
    category: Mapped[str]
    attributes: Mapped[list[str]] = mapped_column(JSONB)
    caption: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float]
    status: Mapped[str] = mapped_column(default="approved")

class Embeddings(Base):
    __tablename__ = "embeddings"

    id = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    entity_type: Mapped[str]
    embedding_vector = mapped_column(ARRAY(Float))

class Post(Base):
    __tablename__ = "posts"

    id = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, unique=True)
    content: Mapped[str] = mapped_column(Text)
    target_subject: Mapped[str]

class AiCostLogs(Base):
    __tablename__ = "ai_cost_logs"

    id = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str]
    called_type: Mapped[str]
    prompt_tokens: Mapped[int]
    completion_tokens: Mapped[int]
    cost_usd: Mapped[float]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class MatchReviews(Base):
    __tablename__ = "match_reviews"

    id = mapped_column(Integer, primary_key=True)
    image_id : Mapped[Optional[int]] = mapped_column(ForeignKey("images.id"), index=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(default="approved")
    similarity_score: Mapped[Optional[float]]
    notes: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

engine = create_engine(DB_URL)

inspector = inspect(engine)
print("Created tables:", inspector.get_table_names())

# with engine.connect() as conn:
Base.metadata.create_all(engine)
print("Tables created successfully!")