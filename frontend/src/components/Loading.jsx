import { Loader2, Sparkles } from "lucide-react";

export default function Loading({ full = false, label = "Loading…", spinner = false }) {
  return (
    <div className={`loading ${full ? "loading-full" : ""} ${spinner ? "loading-spinner" : ""}`}>
      <div className="loading-inner">
        <div className="loading-ring">
          <Sparkles size={22} />
        </div>
        <p>{label}</p>
        {spinner && <Loader2 className="spin" size={16} />}
      </div>
    </div>
  );
}