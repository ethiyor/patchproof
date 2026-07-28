import type { ReviewFinding } from "../api/client";

export type FindingCategoryFilter =
  | "all"
  | "security"
  | "missing_test"
  | "api_contract"
  | "database"
  | "other";

type FindingsListProps = {
  findings: ReviewFinding[];
};

const severityStyles: Record<string, string> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  high: "border-red-200 bg-red-50 text-red-700",
  critical: "border-red-900 bg-red-950 text-red-50",
};

function label(value: string | null): string {
  if (!value) {
    return "Other";
  }
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function groupFindings(findings: ReviewFinding[]): Map<string, ReviewFinding[]> {
  return findings.reduce((groups, finding) => {
    const category = finding.category ?? "other";
    const group = groups.get(category) ?? [];
    group.push(finding);
    groups.set(category, group);
    return groups;
  }, new Map<string, ReviewFinding[]>());
}

function FindingsList({ findings }: FindingsListProps) {
  if (findings.length === 0) {
    return (
      <p className="rounded-md border border-line bg-white p-5 text-sm text-slate-600 shadow-sm">
        No findings match this filter.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {Array.from(groupFindings(findings)).map(([category, groupedFindings]) => (
        <section key={category} className="rounded-md border border-line bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold uppercase text-slate-500">
            {label(category)}
          </h3>
          <div className="mt-4 space-y-4">
            {groupedFindings.map((finding, index) => {
              const severity = finding.severity?.toLowerCase() ?? "unknown";
              const severityClass =
                severityStyles[severity] ??
                "border-slate-200 bg-slate-50 text-slate-600";

              return (
                <article
                  key={`${finding.title}-${finding.file_path ?? "global"}-${index}`}
                  className="border-t border-line pt-4 first:border-t-0 first:pt-0"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h4 className="text-base font-semibold text-ink">{finding.title}</h4>
                      {finding.file_path && (
                        <p className="mt-1 text-xs font-medium text-slate-500">
                          {finding.file_path}
                          {finding.line_start ? `:${finding.line_start}` : ""}
                          {finding.line_end ? `-${finding.line_end}` : ""}
                        </p>
                      )}
                    </div>
                    <span
                      className={`inline-flex w-fit rounded-md border px-2.5 py-1 text-xs font-semibold ${severityClass}`}
                    >
                      {label(severity)}
                    </span>
                  </div>
                  {finding.description && (
                    <p className="mt-3 text-sm leading-6 text-slate-600">
                      {finding.description}
                    </p>
                  )}
                  {finding.evidence && (
                    <p className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-600">
                      {finding.evidence}
                    </p>
                  )}
                  {finding.suggestion && (
                    <p className="mt-3 text-sm font-medium text-slate-700">
                      {finding.suggestion}
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

export default FindingsList;
