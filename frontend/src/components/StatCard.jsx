import { TrendingUp, Sparkles, ArrowUpRight, Scale } from "lucide-react";

const ICONS = {
  payments: Scale,
  volume: TrendingUp,
  savings: Sparkles,
  intl: ArrowUpRight,
};

export default function StatCard({ id, label, value, prefix = "", suffix = "", delta }) {
  const Icon = ICONS[id] || TrendingUp;
  return (
    <div className="stat-card">
      <div className="stat-icon">
        <Icon size={20} />
      </div>
      <div className="stat-body">
        <p className="stat-label">{label}</p>
        <p className="stat-value">
          {prefix}
          {typeof value === "number" ? value.toLocaleString("en-IN") : value}
          {suffix}
        </p>
        {delta && <p className="stat-delta">{delta}</p>}
      </div>
    </div>
  );
}