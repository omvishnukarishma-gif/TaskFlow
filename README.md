# TaskFlow

A full-stack task management application built with FastAPI, SQLAlchemy, and vanilla JavaScript.

---

## Quick Start

```bash
# From the project root, using the shared virtual environment
Z:\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Seed sample data (first run only)
Z:\Scripts\python.exe seed.py

# Open the frontend
# Navigate to http://localhost:8000 in your browser
```

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
| GET    | /tasks/search        | Search by exact title                  | 200     |               |
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

#### `insertion_sort(records, key)` → `(sorted_list, comparisons)`

A comparison-based sort that builds the sorted output one element at a time by inserting each new element into its correct position among the already-sorted prefix.

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
| Space        | O(n)   | One copy of the list     |

**Priority integration** — `GET /tasks?sort=priority` maps priorities to integer weights before sorting:

```python
low = 1,  medium = 2,  high = 3
```

This ensures the numeric order low → medium → high is produced correctly, regardless of alphabetical string ordering.

---

#### `binary_search(sorted_records, target_value, key)` → `(matches, steps)`

A divide-and-conquer search that repeatedly halves the search space.

**Pre-condition:** The input list **must** be sorted ascending by `key`. The `/tasks/search?algo=binary` endpoint automatically sorts via `insertion_sort` before searching.

**How it works:**

```
lo, hi = 0, len(arr) - 1
while lo <= hi:
    steps += 1
    mid = (lo + hi) // 2
    if key(arr[mid]) == target:
        collect arr[mid], expand left + right for duplicates
        break
    elif key(arr[mid]) < target:
        lo = mid + 1
    else:
        hi = mid - 1
```

**Complexity:**

| Case         | Time        |
|--------------|-------------|
| Best case    | O(1)        |
| Average case | O(log n)    |
| Worst case   | O(log n + k) where k = number of duplicates |

---

#### `linear_search(records, target_value, key)` → `(matches, steps)`

Scans every element from left to right, collecting all exact matches.

**How it works:**

```
for each record in records:
    steps += 1
    if key(record) == target:
        collect record
```

Steps always equal `len(records)` regardless of where the target appears.

**Complexity:**

| Case         | Time  |
|--------------|-------|
| Best case    | O(n)  |
| Worst case   | O(n)  |

---

### Algorithm Endpoints

#### `GET /tasks?sort=priority`

Returns all tasks sorted low → medium → high using `insertion_sort`. The custom sort is always called — no Python `sorted()` or `.sort()` is used anywhere in the algorithm modules or routes.

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
| 10   | 27                        | 0.016 ms   | 5            | 4.9 µs      | 10           | 4.1 µs      |
| 500  | 63,863                    | 12.326 ms  | 10           | 8.7 µs      | 500          | 52.8 µs     |
| 3000 | 2,315,018                 | 545.369 ms | 13           | 59.9 µs     | 3,000        | 1,615.7 µs  |

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
Results: 61 passed, 0 failed
ALL TESTS PASSED
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
