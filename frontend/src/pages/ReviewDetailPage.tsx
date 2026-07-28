import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  fetchReview,
  type ChangedFile,
  type ReviewDetailResponse,
  type ReviewFinding,
} from "../api/client";
import FindingsList, { type FindingCategoryFilter } from "../components/FindingsList";
import MissingTestsList from "../components/MissingTestsList";
import RequirementChecklist from "../components/RequirementChecklist";
import RiskBadge from "../components/RiskBadge";
import RiskyFilesList from "../components/RiskyFilesList";

type LoadState = "loading" | "ready" | "error";

type ReviewDetailPageProps = {
  reviewId: string;
  onBack: () => void;
};

const categoryFilters: { id: FindingCategoryFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "security", label: "Security" },
  { id: "missing_test", label: "Missing Test" },
  { id: "api_contract", label: "API Contract" },
  { id: "database", label: "Database" },
  { id: "other", label: "Other" },
];

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatRecommendation(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function classifyFinding(finding: ReviewFinding): FindingCategoryFilter {
  const text = [finding.category, finding.title, finding.description]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (text.includes("security") || text.includes("auth") || text.includes("secret")) {
    return "security";
  }
  if (text.includes("test")) {
    return "missing_test";
  }
  if (text.includes("api") || text.includes("contract")) {
    return "api_contract";
  }
  if (text.includes("database") || text.includes("migration") || text.includes("sql")) {
    return "database";
  }
  return "other";
}

function hasStructuredData(review: ReviewDetailResponse): boolean {
  return (
    review.findings.length > 0 ||
    review.requirement_checks.length > 0 ||
    review.changed_files.length > 0
  );
}

function countRiskyFiles(files: ChangedFile[]): number {
  return files.filter((file) => (file.risk_flags?.length ?? 0) > 0).length;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}

function ReviewDetailPage({ reviewId, onBack }: ReviewDetailPageProps) {
  const [review, setReview] = useState<ReviewDetailResponse | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [filter, setFilter] = useState<FindingCategoryFilter>("all");

  useEffect(() => {
    let isMounted = true;

    async function loadReview() {
      setState("loading");
      try {
        const data = await fetchReview(reviewId);
        if (!isMounted) {
          return;
        }
        setReview(data);
        setState("ready");
      } catch {
        if (isMounted) {
          setState("error");
        }
      }
    }

    void loadReview();

    return () => {
      isMounted = false;
    };
  }, [reviewId]);

  const filteredFindings = useMemo(() => {
    if (!review || filter === "all") {
      return review?.findings ?? [];
    }
    return review.findings.filter((finding) => classifyFinding(finding) === filter);
  }, [filter, review]);

  return (
    <main className="min-h-screen bg-surface text-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-4 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <button
              type="button"
              onClick={onBack}
              className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:border-slate-300"
            >
              Back to reviews
            </button>
            <p className="mt-5 text-sm font-medium uppercase text-slate-500">
              PatchProof report
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">
              Review detail
            </h1>
          </div>
          {review && <RiskBadge level={review.risk_level} />}
        </header>

        {state === "loading" && (
          <section className="flex min-h-72 items-center justify-center rounded-md border border-line bg-white shadow-sm">
            <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-ink" />
              Loading review
            </div>
          </section>
        )}

        {state === "error" && (
          <section className="rounded-md border border-red-200 bg-red-50 p-6 text-sm font-medium text-red-700">
            Failed to load review.
          </section>
        )}

        {state === "ready" && review && (
          <div className="space-y-8">
            <Section title="1. Overview">
              <div className="grid gap-4 sm:grid-cols-4">
                <div className="rounded-md border border-line bg-white p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Risk score</p>
                  <p className="mt-2 text-3xl font-semibold text-ink">
                    {review.risk_score ?? "N/A"}
                  </p>
                </div>
                <div className="rounded-md border border-line bg-white p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Recommendation</p>
                  <p className="mt-2 text-base font-semibold text-ink">
                    {formatRecommendation(review.merge_recommendation)}
                  </p>
                </div>
                <div className="rounded-md border border-line bg-white p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Findings</p>
                  <p className="mt-2 text-3xl font-semibold text-ink">
                    {review.findings.length}
                  </p>
                </div>
                <div className="rounded-md border border-line bg-white p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Created</p>
                  <p className="mt-2 text-sm font-semibold text-ink">
                    {formatDate(review.created_at)}
                  </p>
                </div>
              </div>
            </Section>

            <Section title="2. Original task">
              <p className="rounded-md border border-line bg-white p-5 text-sm leading-6 text-slate-700 shadow-sm">
                {review.task_text ?? "No task text was saved for this review."}
              </p>
            </Section>

            <Section title="3. Merge readiness">
              <p className="rounded-md border border-line bg-white p-5 text-sm leading-6 text-slate-700 shadow-sm">
                PatchProof marked this review as {formatRecommendation(review.merge_recommendation)}.
              </p>
            </Section>

            <Section title="4. Requirement checklist">
              <RequirementChecklist requirements={review.requirement_checks} />
            </Section>

            <Section title="5. Findings by category">
              <div className="flex flex-wrap gap-2">
                {categoryFilters.map((category) => (
                  <button
                    key={category.id}
                    type="button"
                    onClick={() => setFilter(category.id)}
                    className={`rounded-md border px-3 py-2 text-sm font-semibold ${
                      filter === category.id
                        ? "border-blue-600 bg-blue-600 text-white"
                        : "border-line bg-white text-slate-700 hover:border-slate-300"
                    }`}
                  >
                    {category.label}
                  </button>
                ))}
              </div>
              <FindingsList findings={filteredFindings} />
            </Section>

            <Section title="6. Risky files">
              <RiskyFilesList files={review.changed_files} />
            </Section>

            <Section title="7. Missing tests">
              <MissingTestsList
                findings={review.findings}
                requirements={review.requirement_checks}
              />
            </Section>

            <Section title="8. Changed files summary">
              <div className="rounded-md border border-line bg-white p-5 text-sm text-slate-700 shadow-sm">
                {review.changed_files.length} changed files, {countRiskyFiles(review.changed_files)} with risk flags.
              </div>
            </Section>

            <Section title="9. Evidence summary">
              <p className="rounded-md border border-line bg-white p-5 text-sm leading-6 text-slate-700 shadow-sm">
                Evidence is shown inside each requirement and finding row when available.
              </p>
            </Section>

            <Section title="10. Suggested fixes">
              <FindingsList findings={review.findings.filter((finding) => Boolean(finding.suggestion))} />
            </Section>

            <Section title="11. Markdown fallback">
              {!hasStructuredData(review) && review.report_markdown ? (
                <div className="prose max-w-none rounded-md border border-line bg-white p-5 shadow-sm">
                  <ReactMarkdown>{review.report_markdown}</ReactMarkdown>
                </div>
              ) : (
                <p className="rounded-md border border-line bg-white p-5 text-sm text-slate-600 shadow-sm">
                  Structured report data is available above.
                </p>
              )}
            </Section>
          </div>
        )}
      </section>
    </main>
  );
}

export default ReviewDetailPage;
