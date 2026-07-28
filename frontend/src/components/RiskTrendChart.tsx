import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchReviews, type ReviewListItem } from "../api/client";

type ChartPoint = {
  id: string;
  date: string;
  score: number;
  repo: string;
  riskLevel: string;
  recommendation: string;
};

type LoadState = "loading" | "ready" | "empty" | "error";

const riskColors: Record<string, string> = {
  low: "#059669",
  medium: "#d97706",
  high: "#dc2626",
  critical: "#7f1d1d",
  unknown: "#64748b",
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(date);
}

function normalizeRecommendation(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function toChartPoint(review: ReviewListItem): ChartPoint | null {
  if (review.risk_score === null) {
    return null;
  }

  return {
    id: review.review_id,
    date: formatDate(review.created_at),
    score: review.risk_score,
    repo: review.repo_name,
    riskLevel: review.risk_level ?? "unknown",
    recommendation: normalizeRecommendation(review.merge_recommendation),
  };
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload;
  return (
    <div className="rounded-md border border-line bg-white p-3 text-sm shadow-lg">
      <p className="font-semibold text-ink">{point.repo}</p>
      <p className="mt-1 text-slate-600">Risk score: {point.score}</p>
      <p className="text-slate-600">Risk level: {point.riskLevel}</p>
      <p className="text-slate-600">Recommendation: {point.recommendation}</p>
    </div>
  );
}

function RiskDot({ cx, cy, payload }: { cx?: number; cy?: number; payload?: ChartPoint }) {
  if (cx === undefined || cy === undefined) {
    return null;
  }
  const color = riskColors[payload?.riskLevel.toLowerCase() ?? "unknown"] ?? riskColors.unknown;
  return <circle cx={cx} cy={cy} r={4} stroke={color} strokeWidth={2} fill="#ffffff" />;
}

function RiskTrendChart() {
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [state, setState] = useState<LoadState>("loading");

  useEffect(() => {
    let isMounted = true;

    async function loadTrend() {
      setState("loading");
      try {
        const data = await fetchReviews({ limit: 50 });
        if (!isMounted) {
          return;
        }
        setReviews(data.reviews);
        setState(data.reviews.length > 0 ? "ready" : "empty");
      } catch {
        if (isMounted) {
          setState("error");
        }
      }
    }

    void loadTrend();

    return () => {
      isMounted = false;
    };
  }, []);

  const points = useMemo(
    () => reviews.map(toChartPoint).filter((point): point is ChartPoint => point !== null).reverse(),
    [reviews],
  );

  return (
    <section className="rounded-md border border-line bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-ink">Risk trend</h2>
          <p className="text-sm text-slate-500">Latest 50 saved reviews</p>
        </div>
      </div>

      {state === "loading" && (
        <div className="mt-5 flex h-56 items-center justify-center text-sm font-medium text-slate-600">
          Loading trend
        </div>
      )}

      {state === "error" && (
        <p className="mt-5 rounded-md border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
          Failed to load risk trend.
        </p>
      )}

      {state === "empty" && (
        <p className="mt-5 rounded-md border border-line bg-slate-50 p-4 text-sm text-slate-600">
          No review scores are available yet.
        </p>
      )}

      {state === "ready" && points.length > 0 && (
        <div className="mt-5 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 12, right: 12, bottom: 8, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis
                domain={[0, "dataMax + 1"]}
                allowDecimals={false}
                tick={{ fill: "#64748b", fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#2563eb"
                strokeWidth={2}
                dot={<RiskDot />}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export default RiskTrendChart;
