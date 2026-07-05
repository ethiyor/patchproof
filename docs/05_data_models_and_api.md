# 05 — Data Models & API Design

## Database Tables

### users

```sql
id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
email         TEXT UNIQUE NOT NULL
created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

### repositories

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
owner            TEXT NOT NULL
name             TEXT NOT NULL
provider         TEXT NOT NULL DEFAULT 'github'
installation_id  TEXT
created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE (owner, name, provider)
```

---

### pull_requests

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
repository_id   UUID REFERENCES repositories(id)
pr_number       INTEGER NOT NULL
title           TEXT
author          TEXT
base_branch     TEXT
head_branch     TEXT
status          TEXT  -- open | closed | merged
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
UNIQUE (repository_id, pr_number)
```

---

### reviews

```sql
id                    UUID PRIMARY KEY DEFAULT gen_random_uuid()
repository_id         UUID REFERENCES repositories(id)
pull_request_id       UUID REFERENCES pull_requests(id)
task_text             TEXT
diff_text             TEXT
risk_score            INTEGER
risk_level            TEXT  -- low | medium | high | critical
merge_recommendation  TEXT  -- ready | ready_with_comments | needs_changes | do_not_merge
report_markdown       TEXT
created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

### review_findings

```sql
id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
review_id    UUID REFERENCES reviews(id)
category     TEXT
             -- task_alignment | missing_test | security | database
             -- api_contract | config | dependency | bug_risk | out_of_scope
severity     TEXT  -- info | warning | error | critical
title        TEXT NOT NULL
description  TEXT
file_path    TEXT
line_start   INTEGER
line_end     INTEGER
evidence     TEXT
suggestion   TEXT
created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

### requirement_checks

```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
review_id         UUID REFERENCES reviews(id)
requirement_text  TEXT NOT NULL
status            TEXT
                  -- satisfied | partially_satisfied | missing | unclear | out_of_scope_change
evidence          TEXT
reason            TEXT
created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

### changed_files

```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
review_id   UUID REFERENCES reviews(id)
file_path   TEXT NOT NULL
status      TEXT   -- added | modified | deleted | renamed
language    TEXT
additions   INTEGER DEFAULT 0
deletions   INTEGER DEFAULT 0
risk_flags  TEXT[] -- array of matched risky path patterns e.g. ['auth', 'migration']
```

---

## API Endpoints

### POST `/reviews/local`

Used by the CLI to submit a local diff for review.

**Request:**

```json
{
  "repo_name": "papermind",
  "task": "Add PDF upload support with MIME validation and file size limits.",
  "diff": "<raw unified diff text>",
  "changed_files": ["backend/routes/upload.py", "frontend/components/Upload.tsx"],
  "test_output": "... optional pytest output ...",
  "branch": "feat/pdf-upload"
}
```

**Response:**

```json
{
  "review_id": "rev_abc123",
  "status": "completed",
  "report_markdown": "# PatchProof Report\n...",
  "risk_score": 7,
  "risk_level": "high",
  "merge_recommendation": "needs_changes"
}
```

---

### POST `/reviews/github-pr`

Used when a GitHub PR URL is passed.

**Request:**

```json
{
  "pr_url": "https://github.com/user/repo/pull/42",
  "task": "Add PDF upload support."
}
```

**Response:** Same shape as `/reviews/local`.

---

### GET `/reviews/{review_id}`

Returns a saved review.

**Response:**

```json
{
  "review_id": "rev_abc123",
  "created_at": "2026-07-03T10:00:00Z",
  "risk_score": 7,
  "risk_level": "high",
  "merge_recommendation": "needs_changes",
  "report_markdown": "...",
  "findings": [
    {
      "category": "security",
      "severity": "error",
      "title": "No file size limit enforced",
      "file_path": "backend/routes/upload.py",
      "evidence": "No MAX_UPLOAD_SIZE check found in upload handler"
    }
  ],
  "requirement_checks": [
    {
      "requirement_text": "Validate MIME type",
      "status": "missing",
      "reason": "No MIME check found in upload handler"
    }
  ]
}
```

---

### POST `/github/webhook`

Receives GitHub PR events. Must verify `X-Hub-Signature-256` before any processing.

**Required headers:**

```
X-GitHub-Event: pull_request
X-Hub-Signature-256: sha256=<hmac-sha256-of-body>
```

**Body:** Standard GitHub `pull_request` event payload.

**Response:** `202 Accepted` immediately. Analysis runs in background.

**Security rule:** If the signature is missing or invalid, respond with `403` and do not process the payload.

---

### POST `/reviews/{review_id}/comment`

Posts the report back to the GitHub PR as a comment.

**Request:**

```json
{
  "pr_url": "https://github.com/user/repo/pull/42",
  "installation_id": "install_xyz"
}
```

**Response:**

```json
{
  "comment_url": "https://github.com/user/repo/pull/42#issuecomment-123"
}
```

---

### GET `/reviews` (Phase 6 — Dashboard)

Returns a paginated list of reviews for the dashboard.

**Query params:** `?page=1&limit=20&risk_level=high`

**Response:**

```json
{
  "total": 42,
  "reviews": [
    {
      "review_id": "...",
      "repo_name": "papermind",
      "risk_score": 7,
      "risk_level": "high",
      "merge_recommendation": "needs_changes",
      "created_at": "2026-07-03T10:00:00Z"
    }
  ]
}
```
