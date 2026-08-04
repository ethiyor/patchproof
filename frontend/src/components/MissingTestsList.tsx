import type { RequirementCheck, ReviewFinding } from "../api/client";

type MissingTestsListProps = {
  findings: ReviewFinding[];
  requirements: RequirementCheck[];
};

function isMissingTestFinding(finding: ReviewFinding): boolean {
  const text = [
    finding.category,
    finding.title,
    finding.description,
    finding.suggestion,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return text.includes("missing") && text.includes("test");
}

function isMissingTestRequirement(requirement: RequirementCheck): boolean {
  const status = requirement.status?.toLowerCase() ?? "";
  const text = `${requirement.requirement_text} ${requirement.reason ?? ""}`.toLowerCase();
  return (status.includes("missing") || status.includes("fail")) && text.includes("test");
}

function MissingTestsList({ findings, requirements }: MissingTestsListProps) {
  const items = [
    ...findings.filter(isMissingTestFinding).map((finding) => finding.title),
    ...requirements
      .filter(isMissingTestRequirement)
      .map((requirement) => requirement.requirement_text),
  ];

  if (items.length === 0) {
    return (
      <p className="rounded-md border border-line bg-white p-5 text-sm text-slate-600 shadow-sm">
        No missing test cases were recorded.
      </p>
    );
  }

  return (
    <ul className="rounded-md border border-line bg-white p-5 shadow-sm">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-3 py-2 text-sm text-slate-700">
          <input
            type="checkbox"
            readOnly
            className="mt-0.5 h-4 w-4 rounded border-slate-300"
            aria-label={`Missing test case: ${item}`}
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default MissingTestsList;
