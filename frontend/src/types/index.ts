export type ResourceType = "ec2" | "ebs" | "snapshot";
export type FindingType = "idle_ec2" | "unattached_ebs" | "old_snapshot";
export type ValidationStatus = "pending" | "approve" | "needs_review" | "reject";
export type RunStatus = "running" | "completed" | "failed";

export interface Recommendation {
  id: string;
  run_id: string;
  resource_type: ResourceType;
  resource_id: string;
  region: string;
  finding_type: FindingType;
  estimated_monthly_savings_cents: number;
  estimated_monthly_savings_usd: number;
  evidence: Record<string, unknown>;
  validation_status: ValidationStatus;
  validation_reasoning: string | null;
  title: string;
  description: string;
  created_at: string;
}

export interface AnalysisRun {
  id: string;
  status: RunStatus;
  started_at: string;
  completed_at: string | null;
  error: string | null;
  mock_mode: boolean;
  total_recommendations: number;
  total_estimated_savings_cents: number;
  region: string;
}

export interface TriggerResponse {
  run_id: string;
  status: RunStatus;
}
