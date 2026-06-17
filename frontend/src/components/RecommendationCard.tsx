import type { FindingType, Recommendation, ValidationStatus } from "../types";

const FINDING_LABELS: Record<FindingType, string> = {
  idle_ec2: "Idle EC2",
  unattached_ebs: "Unattached EBS",
  old_snapshot: "Old Snapshot",
};

const VALIDATION_STYLES: Record<ValidationStatus, string> = {
  pending: "verdict-pending",
  approve: "verdict-approve",
  needs_review: "verdict-needs_review",
  reject: "verdict-reject",
};

const VALIDATION_LABELS: Record<ValidationStatus, string> = {
  pending: "Pending",
  approve: "Approved",
  needs_review: "Needs review",
  reject: "Rejected",
};

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  return (
    <article className="rec-card">
      <div className="rec-card-head">
        <div>
          <span className="rec-badge">{FINDING_LABELS[rec.finding_type]}</span>
          <h3 className="rec-title">{rec.title}</h3>
          <p className="rec-meta">
            {rec.resource_id} · {rec.region}
          </p>
        </div>
        <div className="rec-savings-col">
          <div className="rec-savings">
            ${rec.estimated_monthly_savings_usd.toFixed(2)}
          </div>
          <div className="rec-savings-unit">/ month</div>
        </div>
      </div>

      <p className="rec-desc">{rec.description}</p>

      <div className={`rec-verdict ${VALIDATION_STYLES[rec.validation_status]}`}>
        <span className="rec-verdict-title">
          Validator: {VALIDATION_LABELS[rec.validation_status]}
        </span>
        {rec.validation_reasoning && (
          <p className="rec-verdict-reason">{rec.validation_reasoning}</p>
        )}
      </div>
    </article>
  );
}
