import type { FindingType, Recommendation, ValidationStatus } from "../types";

const FINDING_LABELS: Record<FindingType, string> = {
  idle_ec2: "Idle EC2",
  unattached_ebs: "Unattached EBS",
  old_snapshot: "Old Snapshot",
};

const VALIDATION_STYLES: Record<ValidationStatus, string> = {
  pending: "bg-slate-100 text-slate-700 border-slate-200",
  approve: "bg-emerald-100 text-emerald-800 border-emerald-200",
  needs_review: "bg-amber-100 text-amber-800 border-amber-200",
  reject: "bg-red-100 text-red-800 border-red-200",
};

const VALIDATION_LABELS: Record<ValidationStatus, string> = {
  pending: "Pending",
  approve: "Approved",
  needs_review: "Needs review",
  reject: "Rejected",
};

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="inline-block rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {FINDING_LABELS[rec.finding_type]}
          </span>
          <h3 className="mt-2 font-semibold text-slate-900">{rec.title}</h3>
          <p className="text-xs text-slate-500">
            {rec.resource_id} · {rec.region}
          </p>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-emerald-700">
            ${rec.estimated_monthly_savings_usd.toFixed(2)}
          </div>
          <div className="text-xs text-slate-500">/ month</div>
        </div>
      </div>

      <p className="mt-3 text-sm text-slate-700">{rec.description}</p>

      <div
        className={`mt-3 rounded-md border px-3 py-2 text-sm ${VALIDATION_STYLES[rec.validation_status]}`}
      >
        <span className="font-semibold">
          Validator: {VALIDATION_LABELS[rec.validation_status]}
        </span>
        {rec.validation_reasoning && (
          <p className="mt-1 leading-snug">{rec.validation_reasoning}</p>
        )}
      </div>
    </article>
  );
}
