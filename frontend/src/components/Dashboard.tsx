import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { AnalysisRun, Recommendation } from "../types";
import { AnalysisStatus } from "./AnalysisStatus";
import { RecommendationList } from "./RecommendationList";

const POLL_INTERVAL_MS = 1500;
const TERMINAL = new Set(["completed", "failed"]);

export function Dashboard() {
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const pollRun = useCallback(
    (runId: string) => {
      stopPolling();
      pollRef.current = window.setInterval(async () => {
        try {
          const latest = await api.getRun(runId);
          setRun(latest);
          if (TERMINAL.has(latest.status)) {
            stopPolling();
            setIsRunning(false);
            if (latest.status === "completed") {
              setRecommendations(await api.getRecommendations(runId));
            } else {
              setError(latest.error ?? "Analysis run failed.");
            }
          }
        } catch (e) {
          stopPolling();
          setIsRunning(false);
          setError(e instanceof Error ? e.message : String(e));
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling],
  );

  const handleRun = useCallback(async () => {
    setError(null);
    setRecommendations([]);
    setIsRunning(true);
    try {
      const { run_id } = await api.triggerAnalysis();
      const initial = await api.getRun(run_id);
      setRun(initial);
      pollRun(run_id);
    } catch (e) {
      setIsRunning(false);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [pollRun]);

  const totalSavingsUsd = recommendations.reduce(
    (sum, r) => sum + r.estimated_monthly_savings_usd,
    0,
  );

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Infrastructure Cost Optimiser</h1>
          <p className="dashboard-subtitle">
            Agentic FinOps analysis of AWS spend, with LLM-validated recommendations.
          </p>
        </div>
        <button onClick={handleRun} disabled={isRunning} className="btn-run">
          {isRunning ? "Analysing…" : "Run Analysis"}
        </button>
      </header>

      <section className="status-panel">
        <AnalysisStatus run={run} totalSavingsUsd={totalSavingsUsd} isPolling={isRunning} />
        {error && <p className="error-banner">{error}</p>}
      </section>

      <RecommendationList
        recommendations={recommendations}
        loading={isRunning && recommendations.length === 0}
      />
    </div>
  );
}
