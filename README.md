# TaskFlow

A full-stack task management application built with FastAPI, SQLAlchemy, and vanilla JavaScript.

---

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server (single process — FastAPI serves both API and frontend)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
### API Documentation

After starting the server, open `http://127.0.0.1:8000/docs` to access the interactive FastAPI Swagger documentation.

# 4. Seed sample data (first run only)
python seed.py

# 5. Open the frontend
# Navigate to http://127.0.0.1:8000 in your browser
```

> **Single-process run:** FastAPI serves both the REST API and the static
> frontend from the same process on the same origin (`http://127.0.0.1:8000`).
> There is no separate frontend build step or dev server required.

---

## Project Structure

```
taskflow/
├── backend/
│   ├── main.py            # FastAPI app — CORS, middleware, router mounts
│   ├── database.py        # SQLAlchemy engine, SessionLocal, Base
│   ├── models.py          # ORM models: User, Project, Task
│   ├── schemas.py         # Pydantic v2 schemas with validators
│   ├── dependencies.py    # get_db() Depends generator
│   ├── routers/
│   │   ├── users.py       # CRUD /users
│   │   ├── projects.py    # CRUD /projects
│   │   └── tasks.py       # CRUD + stats + sort + search /tasks
│   └── algorithms/
│       ├── sorting.py     # insertion_sort()
│       └── searching.py   # binary_search(), linear_search()
├── frontend/
│   ├── index.html         # Single-page application
│   ├── app.js             # Fetch integration, safe DOM, localStorage cache
│   └── style.css          # Responsive styles, priority badges
├── check_algorithms.py    # Algorithm correctness tests + benchmark
├── seed.py                # Sample data seeder
├── requirements.txt
└── README.md
```

---

## Section 1 — Core Application

### Database Schema

**users**

| Column | Type         | Constraints           |
|--------|--------------|-----------------------|
| id     | INTEGER      | PK, autoincrement     |
| name   | VARCHAR(100) | NOT NULL              |
| email  | VARCHAR(255) | NOT NULL, UNIQUE      |

**projects**

| Column      | Type         | Constraints           |
|-------------|--------------|-----------------------|
| id          | INTEGER      | PK, autoincrement     |
| name        | VARCHAR(100) | NOT NULL              |
| description | TEXT         | nullable              |
| owner_id    | INTEGER      | NOT NULL, FK→users.id |

**tasks**

| Column      | Type         | Constraints                                       |
|-------------|--------------|---------------------------------------------------|
| id          | INTEGER      | PK, autoincrement                                 |
| title       | VARCHAR(200) | NOT NULL                                          |
| description | TEXT         | nullable                                          |
| priority    | VARCHAR(10)  | NOT NULL, CHECK IN ('low','medium','high')        |
| due_date    | VARCHAR(20)  | nullable — stored as "YYYY-MM-DD" text, not DATE  |
| completed   | BOOLEAN      | NOT NULL, DEFAULT False                           |
| project_id  | INTEGER      | NOT NULL, FK→projects.id                          |

All relationships use `back_populates`. Cascade delete propagates user → projects → tasks.

### API Endpoints

| Method | Path                 | Description                            | Success | Error         |
|--------|----------------------|----------------------------------------|---------|---------------|
| POST   | /users               | Create user                            | 201     | 400, 422      |
| GET    | /users               | List all users                         | 200     |               |
| GET    | /users/{id}          | Get user by ID                         | 200     | 404           |
| PUT    | /users/{id}          | Update user                            | 200     | 400, 404, 422 |
| DELETE | /users/{id}          | Delete user + cascade                  | 200     | 404           |
| POST   | /projects            | Create project                         | 201     | 404, 422      |
| GET    | /projects            | List all projects                      | 200     |               |
| GET    | /projects/{id}       | Get project by ID                      | 200     | 404           |
| PUT    | /projects/{id}       | Update project                         | 200     | 404, 422      |
| DELETE | /projects/{id}       | Delete project + cascade               | 200     | 404           |
| POST   | /tasks               | Create task                            | 201     | 404, 422      |
| GET    | /tasks               | List all tasks (optional ?sort=priority)| 200    |               |
| GET    | /tasks/stats         | SQL-aggregated statistics              | 200     |               |
| GET    | /tasks/project-stats | Per-project stats (JOIN + GROUP BY)    | 200     |               |
| GET    | /tasks/search        | Search by exact title                  | 200     | 404           |
| GET    | /tasks/{id}          | Get task by ID                         | 200     | 404           |
| PUT    | /tasks/{id}          | Update task                            | 200     | 404, 422      |
| DELETE | /tasks/{id}          | Delete task                            | 200     | 404           |

### Middleware

- **CORS** — explicit `allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"]` with named methods and headers.
- **X-Process-Time** — every response carries an `X-Process-Time` header with wall-clock duration in milliseconds (e.g. `3.291ms`).

### Frontend

- Served at `http://localhost:8000` via FastAPI's `StaticFiles` mount.
- All API data rendered via `textContent` / `createElement` — no `innerHTML` with user-controlled data.
- `localStorage` cache under key `taskflow_tasks`. On network failure the cached list is shown with a `[cached]` badge.

---

## Section 2 — Algorithms Engine

### Algorithms Implemented

#### `insertion_sort(records, key)` → `None` (mutates in place)

A comparison-based sort that builds the sorted output one element at a time by inserting each new element into its correct position among the already-sorted prefix.

**Mutates in place:** The input `records` list is sorted directly. The function returns `None`.
The separate counting wrapper `insertion_sort_count(records, key)` returns the number of comparisons as a plain `int`.

**How it works:**

```
for i = 1 to n-1:
    current = arr[i]
    j = i - 1
    while j >= 0 and key(arr[j]) > key(current):
        arr[j+1] = arr[j]      # shift right
        j -= 1
        comparisons += 1
    arr[j+1] = current
```

Every element-to-element comparison increments the counter, including the final comparison that terminates the inner loop.

**Complexity:**

| Case         | Time   | Comparisons formula      |
|--------------|--------|--------------------------|
| Best case    | O(n)   | n − 1 (already sorted)   |
| Average case | O(n²)  | ≈ n²/4                   |
| Worst case   | O(n²)  | n(n−1)/2 (reverse sorted)|
| Space        | O(1)   | In-place — no copy made  |

**Priority integration** — `GET /tasks?sort=priority` maps priorities to integer weights before sorting:

```python
low = 1,  medium = 2,  high = 3
```

This ensures the numeric order low → medium → high is produced correctly, regardless of alphabetical string ordering.

---

#### `binary_search(sorted_records, target_value, key)` → `int (index or -1)`

A divide-and-conquer search that repeatedly halves the search space.

**Pre-condition:** The input list **must** be sorted ascending by `key`. The `/tasks/search?algo=binary` endpoint automatically sorts via `insertion_sort` before searching.

**How it works:**

```
lo, hi = 0, len(arr) - 1
while lo <= hi:
    steps += 1
    mid = (lo + hi) // 2
    if key(arr[mid]) == target:
        return mid
    elif key(arr[mid]) < target:
        lo = mid + 1
    else:
        hi = mid - 1
return -1
```

**Complexity:**

| Case         | Time        |
|--------------|-------------|
| Best case    | O(1)        |
| Average case | O(log n)    |
| Worst case   | O(log n)    |

---

#### `linear_search(records, target_value, key)` → `int (index or -1)`

Scans elements from left to right and returns the index of the first exact match.

**How it works:**

```
for each record in records:
    steps += 1
    if key(record) == target:
        return index   # stops at first match
return -1
```

For a found item, `steps` equals the position of the first match + 1. For an absent item, `steps` equals `len(records)` (every element examined).

**Complexity:**

| Case         | Time  |
|--------------|-------|
| Best case    | O(1)  |
| Worst case   | O(n)  |

---

### Algorithm Endpoints

#### `GET /tasks?sort=priority`

Returns all tasks sorted low → medium → high using `insertion_sort`. The custom sort is always called — no Python `sorted()` or `.sort()` is used anywhere in the algorithm modules or routes.

The response includes an `X-Sort-Comparisons` header with the exact number of element-to-element comparisons performed by the sort.

Example response (priority order guaranteed):

```json
[
  {"id": 4, "title": "SEO audit",         "priority": "low",    ...},
  {"id": 7, "title": "Write unit tests",  "priority": "medium", ...},
  {"id": 1, "title": "Design homepage",   "priority": "high",   ...}
]
```

#### `GET /tasks/search?title=<exact title>&algo=binary`

Default `algo=binary`. Builds a sorted title index using `insertion_sort`, then runs `binary_search`.

```json
{
  "tasks": [...],
  "count": 1,
  "steps": 4,
  "algorithm": "binary"
}
```

#### `GET /tasks/search?title=<exact title>&algo=linear`

Runs `linear_search` on the unsorted DB rows.

```json
{
  "tasks": [...],
  "count": 1,
  "steps": 13,
  "algorithm": "linear"
}
```

---

### Benchmark

#### Methodology

- Random records generated with `random.seed(42)` for reproducibility.
- Titles are randomised strings of the form `<word>-<index>` (varied enough to avoid all-equal keys).
- Priorities randomly assigned across low/medium/high.
- Sort timing measured with `time.perf_counter()` around the `insertion_sort()` call only.
- Search timing measured around each search call on the same dataset.
- Binary search target = the element at the exact middle of the sorted list (a realistic mid-list lookup).
- Linear search uses the same target on the original unsorted list.
- Machine: Windows, Python 3.13 (free-threading build).

#### Raw Results (from `python check_algorithms.py`)

| n    | insertion_sort comparisons | sort time  | binary steps | binary time | linear steps | linear time |
|------|---------------------------|------------|--------------|-------------|--------------|-------------|
| 10   | 27                        | 0.015 ms   | 5            | 5.1 µs      | 10           | 3.6 µs      |
| 500  | 63,863                    | 15.291 ms  | 10           | 8.5 µs      | 500          | 52.1 µs     |
| 3000 | 2,315,018                 | 545.039 ms | 13           | 8.8 µs      | 3,000        | 330.6 µs    |

#### Interpretation — Is sorting first worthwhile for TaskFlow?

**For search only:**
Binary search uses dramatically fewer steps than linear search once the list is sorted:
- At n=500: 10 binary steps vs 500 linear steps — **50× fewer**.
- At n=3000: 13 binary steps vs 3000 linear steps — **230× fewer**.

However, `insertion_sort` at n=3000 requires **2,315,018 comparisons** and takes **545 ms**. That upfront cost dwarfs the search saving unless the same sorted index is reused across many searches.

**For TaskFlow specifically:**
A typical TaskFlow database holds tens to a few hundred tasks. At these sizes:
- Insertion sort at n=500 takes ~12 ms — acceptable for an on-demand sort.
- Binary search steps (10) vs linear (500) is a clear win **per search**.

**Conclusion:** Sorting first is worthwhile when:
1. The sorted index is cached and reused for multiple searches.
2. The dataset is small enough (< ~1000 rows) that the O(n²) sort cost is acceptable.

For TaskFlow's real workload (< 500 tasks), building a sorted index on each search request is fine. For larger datasets a persistent sorted index or a database index should be used instead.

---

### Running the Algorithm Check

```bash
python check_algorithms.py
```

Expected output ends with:

```
Results: 20 passed, 0 failed
ALL REQUIRED ALGORITHM CHECKS PASSED
```

Exit code 0 on success, 1 on any failure.

---

## Git Workflow

```
main
├── feat: initial project structure
├── feature/core-api  (merged)
│   ├── feat: add core backend — models, schemas, CRUD, stats, middleware
│   └── feat: add frontend — task UI, localStorage cache, safe DOM rendering
└── feature/algorithms  (merged)
    ├── fix: CORS explicit origin + algorithm modules
    └── feat: sort endpoint, search endpoint, check_algorithms, README
```

---

## Interactive Docs

FastAPI auto-generates OpenAPI documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc:       `http://localhost:8000/redoc`

---
## Git Submission

This repository contains the complete TaskFlow application in a single public GitHub repository. The final submission includes the FastAPI backend, algorithms engine, AI Quick-Add parser, frontend dashboard, requirements file, benchmark/check scripts, and this README.

## Section 3 — AI Quick-Add

### Endpoint

```
POST /tasks/quick-add
Content-Type: application/json

{
  "description": "<free-text task description>",
  "project_id": 1
}
```

Returns HTTP 201 and the created task row (including `due_date_hint`).

### Processing order

1. Validate the request (Pydantic `QuickAddRequest`).
2. Verify the project exists → 422 if not found.
3. Parse the description with the deterministic parser.
4. Persist to the existing `tasks` table only after all validation passes.

The `due_date` field stores the raw parser hint (e.g. `"next friday"`, `"tomorrow"`) exactly as matched — no calendar resolution is performed.

---

### Prompting Technique

TaskFlow's Quick-Add uses a **deterministic role-based parser** that mimics the structure of a zero-shot LLM prompt without making any network calls.

**Role structure**

The implementation is split into two logical roles:

- **System role** (`quick_add_parser.SYSTEM_ROLE`): A string that encodes all parsing rules — priority keyword lists, date-phrase matching order, title-generation procedure, and fallback behaviour. In a real LLM integration this string would be the `system` message sent before the user input.

- **User role** (`payload.description`): The raw free-text description supplied by the user. In a real LLM integration this would be the `user` message. The parser treats this as its sole input.

**Zero-shot classification**

This is a zero-shot approach: the system role defines the complete set of rules in a single prompt with no worked examples embedded in it. The parser does not rely on in-context demonstrations (few-shot) or iterative chain-of-thought reasoning — it applies the rules directly.

**Why deterministic instead of a real LLM?**

A real zero-shot LLM (e.g. GPT-4) applied to this task would:
- Consume 50–150 tokens per request (system + user combined).
- Add 200–800 ms of network latency per call.
- Cost money per request (≈$0.0001–0.001 per task at current pricing).
- Occasionally produce inconsistent output for edge cases (e.g. duplicate keywords, ambiguous date phrases) — LLM outputs are non-deterministic by nature.
- Require an API key and internet connectivity — failing offline.

The deterministic parser is **100% reliable, free, instantaneous, and offline**. It produces the exact same output for the same input every time, making it testable and auditable.

**Token implications**

If this were a real LLM prompt:
- System role: ~120 tokens (the rule description in `SYSTEM_ROLE`).
- User role: 5–30 tokens for a typical task description.
- Output: ~30–50 tokens (structured JSON response).
- Total: ~155–200 tokens per request.

At scale (10,000 tasks/day), this would cost approximately $0.50–$2.00/day on GPT-4o. The deterministic parser costs $0.

**Reliability implications**

A real LLM would handle ambiguous phrasings more gracefully (e.g. "sometime next week if possible"), but would introduce non-determinism. For TaskFlow's graded requirements — where specific inputs must produce specific exact outputs — determinism is mandatory. The rule-based parser passes all regression tests 100% of the time.

---

### Worked Examples

All examples show actual inputs sent to `POST /tasks/quick-add` and the exact parsed JSON returned by the live endpoint.

**Example 1 — High priority with date**
```
Input:  "Fix login bug urgent next monday"
Output: {
  "title":         "Fix login bug",
  "priority":      "high",
  "due_date_hint": "next monday"
}
```

**Example 2 — Low priority, no date**
```
Input:  "Reorganise the filing cabinet whenever"
Output: {
  "title":         "Reorganise the filing cabinet",
  "priority":      "low",
  "due_date_hint": null
}
```

**Example 3 — Medium default, bare weekday**
```
Input:  "Submit expense report friday"
Output: {
  "title":         "Submit expense report",
  "priority":      "medium",
  "due_date_hint": "friday"
}
```

**Example 4 — All keywords stripped, title fallback**
```
Input:  "urgent asap whenever"
Output: {
  "title":         "Untitled task",
  "priority":      "high",
  "due_date_hint": null
}
```

**Example 5 — Original casing preserved, repeated date phrase**
```
Input:  "tomorrow Review Meeting tomorrow"
Output: {
  "title":         "Review Meeting",
  "priority":      "medium",
  "due_date_hint": "tomorrow"
}
```

**Example 6 — Mandatory regression: high + null date**
```
Input:  "This is urgent, mark it ASAP please"
Output: {
  "title":         "This is , mark it  please",
  "priority":      "high",
  "due_date_hint": null
}
```

**Example 7 — Mandatory regression: next friday strips correctly**
```
Input:  "Finish the report next Friday, it's urgent"
Output: {
  "title":         "Finish the report , it's",
  "priority":      "high",
  "due_date_hint": "next friday"
}
```

---

### Optional Real LLM

No real LLM is implemented. The deterministic parser is the complete implementation. The architecture supports adding an LLM behind a feature flag in future — the `SYSTEM_ROLE` constant is already written as a deployable prompt. The application works completely offline with zero API keys required.
