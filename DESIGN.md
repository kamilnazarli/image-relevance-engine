# Image Relevance Engine — System Architecture & Design Document

## 1. Overview & Problem Statement

Content platforms frequently struggle with automated image selection for editorial articles. Relying strictly on keyword search yields irrelevant imagery, while relying purely on dense vector similarity creates subtle semantic failures:

* **Metaphor Confusion:** An article on "Database Watchdogs" matches literal photos of guard dogs.
* **Taxonomic / Species Blur:** An article on "Arctic Wolves" matches domestic dogs (e.g., Siberian Huskies) because both sit close in embedding space.
* **Fail-Open Hallucinations:** When no relevant image exists in catalog inventory, standard top-1 retrieval still forces an arbitrary, low-scoring image onto the post.

The **Image Relevance Engine** resolves these issues using a **two-stage architecture**: coarse vector recall paired with an editorial LLM Mismatch Guard operating under a strict **fail-closed** policy.

---

## 2. High-Level Architecture

```text
                    +------------------------------------------+
                    |           Offline Data Ingestion         |
                    +------------------------------------------+
                                          |
          [Raw Images]                    |                [Blog Posts]
                |                         |                      |
      (Vision Pipeline:                   |             (Structured Framing:
       Gemini / Groq Fallback)            |              Subject/Title/Body)
                |                         |                      |
      [Structured Metadata]               |                      |
                |                         |                      |
      (Embedding Pipeline)                |             (Embedding Pipeline)
                |                         |                      |
                +-----------> [PostgreSQL + pgvector] <----------+
                                          |
                                          |
                    +------------------------------------------+
                    |          Online Inference / API          |
                    +------------------------------------------+
                                          |
                                  POST /posts
                               (Title, Body, Target)
                                          |
                             [Query Embedding Generation]
                                          |
                             Stage 1: Coarse Vector Search
                             (Cosine Similarity >= 0.40)
                                          |
                                  Top-3 Candidates
                                          |
                             Stage 2: LLM Mismatch Guard
                               (Gemini Structured Output)
                             - Positive species validation
                             - Metaphor / domain rejection
                             - Lifestyle / setting integrity
                             - Fail-closed on missing inputs
                                          |
                      +-------------------+-------------------+
                      |                                       |
                  [Approved]                              [Rejected]
                      |                                       |
             Return Image Asset                     Return null / unmatched
        Log to match_reviews (status='approved')    Log to match_reviews (status='rejected')
```

---

## 3. Core Architectural Decisions

### 3.1 Two-Stage Retrieval

#### Stage 1 — High-Recall Vector Retrieval

The system reduces an arbitrary catalog down to the top 3 candidates using vector similarity.

Cosine similarity is derived from cosine distance:

```text
Similarity = 1 - Cosine Distance(u, v)
```

A relaxed similarity floor (`>= 0.40`) ensures candidates are not prematurely dropped before contextual reasoning can evaluate them.

#### Stage 2 — High-Precision Verification (Mismatch Guard)

An LLM evaluates the candidates against the post.

Vector models compute semantic proximity, but cannot reliably reason through symbolic rules such as:

> "A French Bulldog cannot illustrate an article about gray wolves."

The Mismatch Guard therefore performs contextual validation before an image is approved.

---

### 3.2 Symmetrical Embedding Representation

Embedding models can be sensitive to formatting, syntax, and keyword order. Discrepancies between post and image representations can therefore cause systematic vector drift.

Both entities are embedded using symmetrical structured representations.

#### Post Text

```text
Subject: {target_subject}
Title: {title}
Description: {content}
```

#### Image Text

```text
Subject: {subject}
Category: {category}
Description: {caption}
Attributes: {attr_1}, {attr_2}, ...
```

Using consistent semantic fields improves the alignment between the post representation and the image representation.

---

### 3.3 Fail-Closed vs. Fail-Open Policy

#### Fail-Open (Anti-pattern)

The system approves an image unless an explicit violation is detected.

This can lead to nonsensical matches when data is malformed, incomplete, or absent.

#### Fail-Closed (Engine Policy)

The system requires verified evidence of contextual alignment before approving an image.

If candidates lack sufficient similarity, an API timeout occurs, or required inputs are missing, the system defaults to:

```json
{
  "matched": false,
  "image_id": null,
  "status": "rejected"
}
```

**Design principle:**

> Showing no image is preferred over showing an incorrect image.

---

## 4. Database Schema Design

The system runs on **PostgreSQL** with the **pgvector** extension.

```text
       +------------------+             +------------------------+
       |      images      |             |         posts          |
       +------------------+             +------------------------+
       | id (PK)          |             | id (PK)                |
       | file_path (UQ)   |             | title (UQ)              |
       | source_url       |             | content                |
       | created_at       |             | target_subject         |
       +--------+---------+             +-----------+------------+
                |                                   |
                | 1:1                               | 1:N
                v                                   v
       +------------------+             +------------------------+
       |  image_metadata  |             |     match_reviews      |
       +------------------+             +------------------------+
       | id (PK)          |             | id (PK)                |
       | image_id (FK, UQ)|             | post_id (Indexed)      |
       | subject          |             | image_id (FK, Nullable)|
       | category         |             | status                 |
       | attributes(JSONB)|             | similarity_score       |
       | caption          |             | notes (JSONB)          |
       | confidence       |             | created_at             |
       | status           |             +------------------------+
       +------------------+
                |
                +---------------+
                |               |
                v               v
       +------------------+   +-------------------+
       |    embeddings    |   |    ai_cost_logs   |
       +------------------+   +-------------------+
       | id (PK)          |   | id (PK)           |
       | entity_id (Idx)  |   | model_name        |
       | entity_type      |   | called_type       |
       | embedding_vector |   | prompt_tokens     |
       | CONSTRAINT UQ    |   | completion_tokens |
       | (entity_id, type)|   | cost_usd          |
       +------------------+   +-------------------+
```

### Table Responsibilities & Constraints

#### 1. `images`

Source catalog records containing filesystem paths and origin URLs.

#### 2. `image_metadata`

Stores outputs from the vision pipeline.

Contains:

* Detected subject
* Category
* Raw JSON attributes
* Descriptive caption
* Vision model confidence score

#### 3. `embeddings`

Stores 768-dimensional vectors generated by `gemini-embedding-2`.

The table enforces:

```sql
UNIQUE (entity_id, entity_type)
```

This prevents duplicate vectors for the same entity and entity type.

#### 4. `posts`

Stores ingested blog post drafts and target metadata.

#### 5. `match_reviews`

Provides an audit trail of every image evaluation attempt.

Important constraints:

* `image_id` is nullable, allowing rejected matches to be logged without foreign-key violations.
* `post_id` is indexed.
* `image_id` is indexed rather than unique, allowing a single catalog image to legitimately pair with multiple distinct posts.

#### 6. `ai_cost_logs`

Tracks token consumption and API costs across Gemini and Groq API calls.

---

## 5. Pipeline Stages & Execution

### Stage 1: Vision Ingestion — `process_images.py`

1. Reads unanalyzed images from `images`.
2. Encodes local image binaries to Base64.
3. Calls the primary vision model (`gemini-2.5-flash`) using structured JSON output with the `ImageAnalysisResult` schema.
4. If the primary model is rate-limited or unavailable, automatically falls back to `qwen/qwen-2.5-vl-72b` through Groq.
5. Flags images with confidence `< 0.70` as `flagged_low_confidence` while inserting validated records into `image_metadata`.

---

### Stage 2: Vector Ingestion — `generate_embeddings.py`

1. Extracts approved rows from `image_metadata` that do not already have an embedding.
2. Compiles the symmetrical image representation using:

   * `Subject`
   * `Category`
   * `Description`
   * `Attributes`
3. Calls `gemini-embedding-2`.
4. Inserts or updates vectors using:

```sql
ON CONFLICT (entity_id, entity_type) DO UPDATE
```

---

### Stage 3: Recommendation Engine & Validation Guard — `search_engine.py`

1. Embeds the incoming post request using the symmetrical post template.
2. Computes cosine similarity scores against image vectors stored in the database.
3. Selects the top 3 candidates meeting the baseline criteria:

   * Similarity `>= 0.40`
   * Vision confidence `>= 0.70`
4. Evaluates candidates sequentially through `llm_guard()`.
5. Enforces the Pydantic `GuardDecision` schema to guarantee valid structured output.
6. The guard evaluates:

   * Positive species validation
   * Domain/metaphor mismatches
   * Setting and lifestyle context
7. Approves the first compliant candidate.
8. If no candidate passes validation, returns an explicit rejection.
9. Commits evaluation details, candidate IDs, similarity scores, and rationale to `match_reviews`.

---

## 6. Failure Modes & Mitigations

| Failure Mode                     | Root Cause                                              | Architectural Mitigation                                                                                           |
| -------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Rate Limit Lockup (HTTP 429)** | Synchronous retry loop in an async framework            | Client-level HTTP timeouts (`15s`) and migration of blocking database/network calls away from FastAPI's event loop |
| **Species Substitution**         | Close proximity in embedding space (e.g., dog vs. wolf) | Strict LLM prompt rules enforcing positive species boundaries over biological-family proximity                     |
| **Metaphoric False Positives**   | Shared lexical vocabulary (e.g., software "watchdog")   | Guard prompt explicitly cross-checks target domain against image attributes                                        |
| **Catalog Exhaustion**           | No image matches the post content                       | Fail-closed mechanism inserts `image_id = NULL` and surfaces structured rejection messages                         |

---

## 7. Design Principles

The Image Relevance Engine is built around four primary principles:

1. **High recall before reasoning**

   Vector search should retrieve plausible candidates without being overly restrictive.

2. **High precision before approval**

   Semantic similarity alone is insufficient for final image selection.

3. **Fail closed**

   Uncertainty, missing information, API failures, and insufficient evidence should result in rejection rather than an arbitrary image.

4. **Auditability**

   Every evaluation should produce structured records containing the candidate, similarity score, decision, and rationale.
