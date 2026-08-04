import type { RiskLevel } from "../api/client";

type RiskBadgeProps = {
  level: RiskLevel | null;
};

const riskStyles: Record<string, string> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  high: "border-red-200 bg-red-50 text-red-700",
  critical: "border-red-900 bg-red-950 text-red-50",
};

function RiskBadge({ level }: RiskBadgeProps) {
  const normalized = level?.toLowerCase() ?? "unknown";
  const label = normalized.charAt(0).toUpperCase() + normalized.slice(1);
  const className =
    riskStyles[normalized] ?? "border-slate-200 bg-slate-50 text-slate-600";

  return (
    <span
      className={`inline-flex min-w-20 items-center justify-center rounded-md border px-2.5 py-1 text-xs font-semibold ${className}`}
    >
      {label}
    </span>
  );
}

export default RiskBadge;
