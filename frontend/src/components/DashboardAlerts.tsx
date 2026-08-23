import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import api from "../lib/api";
import type { Anomaly } from "../types";

const fetchAnomalies = async (): Promise<Anomaly[]> => {
  const { data } = await api.get("/analytics/anomalies?days=30");
  return data;
};

const severityClasses = {
  high: "bg-red-50 text-red-800 border-red-200",
  medium: "bg-yellow-50 text-yellow-800 border-yellow-200",
  low: "bg-blue-50 text-blue-700 border-blue-200",
};

export function DashboardAlerts() {
  const { data: anomalies, isLoading } = useQuery<Anomaly[]>({
    queryKey: ["anomalies"],
    queryFn: fetchAnomalies,
  });

  return (
    <div className="legacy-dark-card p-5 rounded-2xl border shadow-xl shadow-black/10 h-full">
      <h2 className="text-lg font-bold tracking-tight mb-4">Alerts</h2>
      {isLoading ? (
        <div className="h-32 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        </div>
      ) : !anomalies || anomalies.length === 0 ? (
        <div className="h-32 flex items-center justify-center text-center">
          <p className="text-sm legacy-muted">No unusual activity detected in the last 30 days.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {anomalies.slice(0, 3).map((a) => (
            <div key={a.transaction_id} className={`p-3 rounded-lg border ${severityClasses[a.severity]}`}>
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <p className="text-xs">{a.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}