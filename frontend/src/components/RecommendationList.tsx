import type { Recommendation } from "../types";
import { RecommendationCard } from "./RecommendationCard";

interface Props {
  recommendations: Recommendation[];
  loading: boolean;
}

export function RecommendationList({ recommendations, loading }: Props) {
  if (loading) {
    return (
      <div className="rec-grid">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rec-skeleton" />
        ))}
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <p className="rec-empty">
        No recommendations yet. Run an analysis to surface cost-saving opportunities.
      </p>
    );
  }

  return (
    <div className="rec-grid">
      {recommendations.map((rec) => (
        <RecommendationCard key={rec.id} rec={rec} />
      ))}
    </div>
  );
}
