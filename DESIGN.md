## Problem Statement & Mission
- Our mission is to build a system that looks at an image library, understands what's actually in each image, matches it and tags it. This happens based on what the images mean, not filenames or keywords.
- Aimed behavior: a blog post about red fox has to match a red fox image. A similar looking wolf image has to be rejected. And if no image is a good match, the system says no instead of guessing.

## Vision Model Output Schema (Pydantic / Structured JSON)
```json
{
  "subject": "red fox",
  "category": "animal",
  "attributes": ["orange fur", "wild", "forest"],
  "caption": "A red fox standing in a forest",
  "confidence": 0.94
}
```
Outputs below 0.70 confidence trigger an automated flag for review instead of ingestion into the matching pool.

## Matching Pipeline & Mismatch Guard Strategy


## Explicit Non-Goals
- **No Full Frontend UI:** The system will not provide an interactive client web app, React build, or complex CSS interface. Endpoints and basic API payloads serve as the operational interface.
- **No Real-Time Web Scraping:** The engine will not fetch live web links or search engines; image retrieval is strictly scoped to the local curated corpus.
- **No Dynamic Model Benchmarking:** The engine does not benchmark multiple vision or embedding models simultaneously; it remains scoped to a single vision-embedding pair.  
