import type { RequirementCheck } from "../api/client";

type RequirementChecklistProps = {
  requirements: RequirementCheck[];
};

const statusStyles: Record<string, string> = {
  satisfied: "bg-emerald-50 text-emerald-700 border-emerald-200",
  pass: "bg-emerald-50 text-emerald-700 border-emerald-200",
  met: "bg-emerald-50 text-emerald-700 border-emerald-200",
  partial: "bg-amber-50 text-amber-700 border-amber-200",
  missing: "bg-red-50 text-red-700 border-red-200",
  fail: "bg-red-50 text-red-700 border-red-200",
};

function normalizeStatus(status: string | null): string {
  return status?.toLowerCase().replace(/\s+/g, "_") ?? "unknown";
}

function RequirementChecklist({ requirements }: RequirementChecklistProps) {
  if (requirements.length === 0) {
    return (
      <p className="rounded-md border border-line bg-white p-5 text-sm text-slate-600 shadow-sm">
        No structured requirement checks were saved for this review.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3">Requirement</th>
            <th className="w-32 px-4 py-3">Status</th>
            <th className="px-4 py-3">Evidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {requirements.map((requirement, index) => {
            const normalized = normalizeStatus(requirement.status);
            const style =
              statusStyles[normalized] ??
              "bg-slate-50 text-slate-600 border-slate-200";

            return (
              <tr key={`${requirement.requirement_text}-${index}`}>
                <td className="px-4 py-4 font-medium text-ink">
                  {requirement.requirement_text}
                </td>
                <td className="px-4 py-4">
                  <span
                    className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${style}`}
                  >
                    {requirement.status ?? "Unknown"}
                  </span>
                </td>
                <td className="px-4 py-4 text-slate-600">
                  {requirement.evidence ?? requirement.reason ?? "No evidence saved."}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default RequirementChecklist;
