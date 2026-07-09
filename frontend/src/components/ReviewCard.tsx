import type { ReviewListItem } from "../api/client";
import RiskBadge from "./RiskBadge";

type ReviewCardProps = {
  review: ReviewListItem;
};

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
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function ReviewCard({ review }: ReviewCardProps) {
  return (
    <article className="rounded-md border border-line bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-ink">
            {review.repo_name}
          </h2>
          <p className="mt-1 text-sm text-slate-500">{formatDate(review.created_at)}</p>
        </div>
        <RiskBadge level={review.risk_level} />
      </div>

      <div className="mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Risk score
          </p>
          <p className="mt-1 text-2xl font-semibold text-ink">
            {review.risk_score ?? "N/A"}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Merge recommendation
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-700">
            {formatRecommendation(review.merge_recommendation)}
          </p>
        </div>
      </div>
    </article>
  );
}

export default ReviewCard;
