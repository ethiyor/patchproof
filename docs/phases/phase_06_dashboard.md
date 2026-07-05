# Phase 6 — Dashboard

**Prerequisites:** Phase 4 complete. Reviews are persisted in PostgreSQL.
**Reference docs:** [05_data_models_and_api.md](../05_data_models_and_api.md)

---

## Overview

Build a React web dashboard that displays review history, per-PR risk scores, finding categories, and risk trends. This is a read-only UI — no new analysis is triggered from here.

---

## Milestone 6.1 — Backend List Endpoint

**Goal:** A paginated `GET /reviews` endpoint the dashboard can query.

**Files to modify:**

```
backend/api/reviews.py
backend/schemas/review_schemas.py
```

**Tasks:**
- Implement `GET /reviews?page=1&limit=20&risk_level=high`
- Return: `total`, `reviews` list with `review_id`, `repo_name`, `risk_score`, `risk_level`, `merge_recommendation`, `created_at`
- Add CORS middleware to `backend/main.py` — allow `http://localhost:5173` (Vite dev server)
- Integration test with `httpx.AsyncClient`

**Done when:**
```bash
GET /reviews
# Returns list of reviews from the database
```

---

## Milestone 6.2 — React + Vite + Tailwind Setup

**Goal:** A running React app with Tailwind that can fetch from the backend.

**Files to create:**

```
frontend/package.json
frontend/vite.config.ts
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/api/client.ts
frontend/index.html
```

**Tasks:**
- `npm create vite@latest frontend -- --template react-ts`
- Install Tailwind CSS, `axios` or `fetch`
- Create `src/api/client.ts` — base Axios instance pointing at `VITE_API_URL` env variable
- Verify `npm run dev` starts without errors and renders a placeholder page

**Done when:**
```bash
cd frontend && npm run dev
# React app running at http://localhost:5173
```

---

## Milestone 6.3 — Reviews List Page

**Goal:** A page that fetches and displays all reviews.

**Files to create:**

```
frontend/src/pages/ReviewsPage.tsx
frontend/src/components/RiskBadge.tsx
frontend/src/components/ReviewCard.tsx
```

**Tasks:**
- Fetch `GET /reviews` on mount, show loading spinner during fetch
- Display each review as a card: repo name, risk badge, merge recommendation, date
- `RiskBadge` component: green for Low, yellow for Medium, red for High, dark red for Critical
- Handle empty state: "No reviews yet. Run patchproof review to get started."
- Handle fetch error: "Failed to load reviews."

**Done when:**
- Page loads and shows real reviews from the database
- Risk badges display correct color per level

---

## Milestone 6.4 — Review Detail Page

**Goal:** A page that shows the full report for a single review.

**Files to create:**

```
frontend/src/pages/ReviewDetailPage.tsx
frontend/src/components/RequirementChecklist.tsx
frontend/src/components/FindingsList.tsx
frontend/src/components/RiskyFilesList.tsx
frontend/src/components/MissingTestsList.tsx
```

**Tasks:**
- Fetch `GET /reviews/{id}` on mount
- Render all 11 report sections using structured data (not raw Markdown)
- `RequirementChecklist`: table with requirement text, status icon, evidence
- `FindingsList`: grouped by category, shows severity badge, file path, description
- `RiskyFilesList`: table of risky files with risk category
- `MissingTestsList`: checkbox list of missing test cases
- Render `report_markdown` as a fallback if structured data is unavailable (use `react-markdown`)

**Done when:**
- Clicking a review in the list opens the detail page with all sections populated

---

## Milestone 6.5 — Risk Trend Chart

**Goal:** A chart showing risk scores over time across all reviews.

**Files to create:**

```
frontend/src/components/RiskTrendChart.tsx
```

**Tasks:**
- Install `recharts`
- Fetch recent reviews from `GET /reviews?limit=50`
- Render `LineChart` with: x-axis = date, y-axis = risk score, color-coded by risk level
- Show tooltip on hover: repo name, risk score, merge recommendation

**Done when:**
- Chart renders with real data from the database
- Tooltip shows correct info on hover

---

## Milestone 6.6 — Finding Filters + Production Build

**Goal:** Filter findings by category, and build the frontend for production.

**Files to modify:**

```
frontend/src/pages/ReviewDetailPage.tsx
```

**Tasks:**
- Add category filter buttons above `FindingsList`: All / Security / Missing Test / API Contract / Database / Other
- Filter findings client-side by selected category
- `npm run build` produces a static bundle
- Update `docker-compose.yml` to serve the frontend build via FastAPI static files or a separate Nginx service
- Update backend CORS to allow the production frontend URL

**Done when:**
- Clicking a category filter shows only findings of that type
- `npm run build` succeeds with no TypeScript errors
- Dashboard accessible from `docker compose up`

---

## Phase 6 Acceptance Criteria

```
✓ Reviews list page shows all reviews with risk badges
✓ Review detail page shows all sections with structured data
✓ Risk trend chart renders with real data
✓ Finding filter works for all categories
✓ Loading and error states handled in all pages
✓ npm run build succeeds with no TypeScript errors
✓ CORS configured correctly for both dev and production
```
