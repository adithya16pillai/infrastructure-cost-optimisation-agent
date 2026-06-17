import type { AnalysisRun, RunStatus } from "../types";

const STATUS_STYLES: Record<RunStatus, string> = {
  running: "status-running",
  completed: "status-completed",
  failed: "status-failed",
};

interface Props {
  run: AnalysisRun | null;
  totalSavingsUsd: number;
  isPolling: boolean;
}

export function AnalysisStatus({ run, totalSavingsUsd, isPolling }: Props) {
  if (!run) {
    return (
      <p className="status-empty">
        No analysis run yet. Click <span className="status-emphasis">Run Analysis</span> to start.
      </p>
    );
  }

  const label = isPolling ? "running" : run.status;

  return (
    <div className="status-row">
      <span className={`status-badge ${STATUS_STYLES[label as RunStatus]}`}>
        {label}
      </span>
      <span className="status-meta">
        Run <code className="status-code">{run.id.slice(0, 8)}</code>
      </span>
      <span className="status-meta">
        {run.mock_mode ? "Mock data" : "Live AWS"} · {run.region}
      </span>
      {run.status === "completed" && (
        <>
          <span className="status-meta">
            {run.total_recommendations} recommendations
          </span>
          <span className="status-savings">
            ${totalSavingsUsd.toFixed(2)}/mo potential savings
          </span>
        </>
      )}
      {run.error && <span className="status-error">Error: {run.error}</span>}
    </div>
  );
}
