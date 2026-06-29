import type {
  AnalysisRun,
  CloudProvider,
  Recommendation,
  TriggerResponse,
} from "../types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${detail}`);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  triggerAnalysis: (provider: CloudProvider) =>
    request<TriggerResponse>("/analysis/run", {
      method: "POST",
      body: JSON.stringify({ provider }),
    }),

  getRun: (runId: string) => request<AnalysisRun>(`/analysis/${runId}`),

  getRecommendations: (runId: string) =>
    request<Recommendation[]>(
      `/recommendations?run_id=${encodeURIComponent(runId)}`,
    ),

  health: () =>
    request<{
      status: string;
      mock_cloud: boolean;
      llm_enabled: boolean;
      providers: CloudProvider[];
    }>("/health"),
};
