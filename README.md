# Image Relevance Engine

## An end-to-end backend system that pairs blog posts with catalog images using vector similarity, multimodal vision analysis, and LLM-based verification.

Image relevance engine is AI-powered engine which matches given blog posts with existing catalog images using vector similarity. This allows users to upload content of their posts and search for the most relevant image in the catalog. The engine stores the embeddings of both images and posts then matches them based on cosine similarity.

## Features

- Image metadata extraction
- Vector similarity search
- LLM mismatch detection

## Architecture

                    ┌─────────────────────────┐
                    │      Data Ingestion     │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
        ┌─────▼─────┐                         ┌─────▼─────┐
        │   Images  │                         │ Blog Posts│
        └─────┬─────┘                         └─────┬─────┘
              │                                     │
       Vision Analysis                        Text Processing
              │                                     │
              └──────────────────┬──────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ PostgreSQL + pgvector   │
                    └────────────┬────────────┘
                                 │
                                 │
                    ┌────────────▼────────────┐
                    │    Online Inference     │
                    │    POST /recommendation │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Vector Similarity      │
                    │       Retrieval         │
                    └────────────┬────────────┘
                                 │
                              Top-K
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    LLM Mismatch Guard   │
                    │     (Validation)        │
                    └────────────┬────────────┘
                                 │
                       ┌─────────┴─────────┐
                       ▼                   ▼
                  ┌─────────┐         ┌─────────┐
                  │ Approved│         │ Rejected│
                  └────┬────┘         └────┬────┘
                       │                   │
                       ▼                   ▼
                  Image Match          No Match

## Tech stack

- Runtime/Web API: Python, FastAPI, Uvicorn
- Database: PostgreSQL, pgvector, psycopg, SQLAlchemy
- AI Models:
    - Vision: Google Gemini(gemini-2.5-flash), Groq(qwen-2.5-vl-72b)(fallback)
    - Text Embeddings: Google Gemini(gemini-embedding-2)
    - Validation Guard: Google Gemini(gemini-2.5-flash)
- Validation: Pydantic

## Getting started

1. Prerequisites
- Python 3.11 or higher
- Running instance of PostgreSQL with pgvector installed
- API keys:
    - [Google AI Studio API KEY](https://aistudio.google.com/api-keys?project=gen-lang-client-0466515709)
    - [Groq Cloud API KEY](https://console.groq.com/keys) (used for fallback vision analysis)

2. Installation:
    1. clone the project
    ```bash
    git clone [https://github.com/kamilnazarli/image-relevance-engine.git](https://github.com/kamilnazarli/image-relevance-engine.git)
    cd image-relevance-engine
    ```
    2. Setup virtual environment
    ```bash
    python -m venv .venv
    # On Linux
    source .venv/bin/activate
    # On Windows:
    .\.venv\Scripts\activate.ps1
    ```
    3. Install dependencies
    ```bash
    pip install -r requirements.txt
    ```
    4. Environment configuration
    ```bash
    cp .env.example .env
    ```

## Database setup & Pipeline execution

Run scripts sequentially as shown below:

**Step 1:** Create all relational databases
```bash
python -m src.models
```

**Step 2:** Seed catalog images and sample posts
```bash
python -m src.image_utils.seed_image
python -m src.image_utils.seed_posts
```

**Step 3:** Run vision analysis
```bash
python -m src.image_utils.process_images
```

**Step 4:** Generate embeddings
```bash
python -m src.generate_embeddings
```

## Running the API

Start the FastAPI with Uvicorn:
```bash
uvicorn src.main:app --reload --port 8000
```

Interactive documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API documentation

POST /recommendation
Submits a blog post draft, calculates similarit with against existing catalog. Then, evaluates top canditates through LLM guard and records the outcome.

Request body

```json
{
  "title": "Essential Care and Cold Weather Tips for French Bulldogs",
  "content": "French Bulldogs are prone to catching chills due to their short single coats. During colder months, dressing your Frenchie in a warm hoodie or sweater keeps them comfortable during outdoor walks.",
  "target_subject": "French Bulldog"
}
```

Successful response

```json

```

Will be completed soon...