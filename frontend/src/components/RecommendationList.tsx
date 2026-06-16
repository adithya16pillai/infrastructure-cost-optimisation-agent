import type { Recommendation } from "../types";
import { RecommendationCard } from "./RecommendationCard";

interface Props {
  recommendations: Recommendation[];
  loading: boolean;
}

export function RecommendationList({ recommendations, loading }: Props) {
  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-40 animate-pulse rounded-lg border border-slate-200 bg-white"
          />
        ))}
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No recommendations yet. Run an analysis to surface cost-saving opportunities.
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {recommendations.map((rec) => (
        <RecommendationCard key={rec.id} rec={rec} />
      ))}
    </div>
  );
}
