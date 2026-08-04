import type { ChangedFile } from "../api/client";

type RiskyFilesListProps = {
  files: ChangedFile[];
};

function RiskyFilesList({ files }: RiskyFilesListProps) {
  const riskyFiles = files.filter((file) => (file.risk_flags?.length ?? 0) > 0);

  if (riskyFiles.length === 0) {
    return (
      <p className="rounded-md border border-line bg-white p-5 text-sm text-slate-600 shadow-sm">
        No risky files were flagged in this review.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-line bg-white shadow-sm">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3">File</th>
            <th className="px-4 py-3">Language</th>
            <th className="px-4 py-3">Change</th>
            <th className="px-4 py-3">Risk category</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {riskyFiles.map((file) => (
            <tr key={file.file_path}>
              <td className="px-4 py-4 font-medium text-ink">{file.file_path}</td>
              <td className="px-4 py-4 text-slate-600">{file.language ?? "Unknown"}</td>
              <td className="px-4 py-4 text-slate-600">
                +{file.additions} / -{file.deletions}
              </td>
              <td className="px-4 py-4">
                <div className="flex flex-wrap gap-2">
                  {file.risk_flags?.map((flag) => (
                    <span
                      key={`${file.file_path}-${flag}`}
                      className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default RiskyFilesList;
