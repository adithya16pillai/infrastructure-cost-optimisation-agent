import type { AnalysisRun, RunStatus } from "../types";

const STATUS_STYLES: Record<RunStatus, string> = {
  running: "bg-blue-100 text-blue-700",
  completed: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

interface Props {
  run: AnalysisRun | null;
  totalSavingsUsd: number;
  isPolling: boolean;
}

export function AnalysisStatus({ run, totalSavingsUsd, isPolling }: Props) {
  if (!run) {
    return (
      <p className="text-sm text-slate-500">
        No analysis run yet. Click <span className="font-medium">Run Analysis</span> to start.
      </p>
    );
  }

  const label = isPolling ? "running" : run.status;

  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <span
        className={`rounded-full px-3 py-1 font-medium capitalize ${STATUS_STYLES[label as RunStatus]}`}
      >
        {label}
      </span>
      <span className="text-slate-600">
        Run <code className="text-xs">{run.id.slice(0, 8)}</code>
      </span>
      <span className="text-slate-600">
        {run.mock_mode ? "Mock data" : "Live AWS"} · {run.region}
      </span>
      {run.status === "completed" && (
        <>
          <span className="text-slate-600">
            {run.total_recommendations} recommendations
          </span>
          <span className="font-semibold text-emerald-700">
            ${totalSavingsUsd.toFixed(2)}/mo potential savings
          </span>
        </>
      )}
      {run.error && <span className="text-red-600">Error: {run.error}</span>}
    </div>
  );
}
