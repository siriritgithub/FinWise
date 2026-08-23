import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Loader2 } from "lucide-react";
import api from "../lib/api";
import { formatINR } from "../lib/utils";
import type { CashflowForecast } from "../types";

const fetchCashflow = async (): Promise<CashflowForecast> => {
  const { data } = await api.get("/analytics/cashflow?days=30");
  return data;
};

export function CashflowChart() {
  const { data, isLoading } = useQuery<CashflowForecast>({
    queryKey: ["cashflow"],
    queryFn: fetchCashflow,
  });

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!data) return <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>;

  const formattedData = data.forecast.map(d => ({
    ...d,
    balance: d.predicted_balance,
    date: new Date(d.date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }),
  }));

  return (
    <div className="legacy-dark-card p-5 rounded-2xl border shadow-xl shadow-black/10">
      <h2 className="text-lg font-bold tracking-tight mb-1">Cash Flow Forecast</h2>
      <p className="text-xs legacy-muted mb-4">Predicted balance for the next 30 days</p>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={formattedData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#26354d" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#334155" }} tickLine={{ stroke: "#334155" }} />
          <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={{ stroke: "#334155" }} tickLine={{ stroke: "#334155" }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            formatter={(value) => [formatINR(Number(value ?? 0)), "Balance"]}
            labelStyle={{ fontSize: 12 }}
            contentStyle={{ fontSize: 12, borderRadius: '0.75rem', background: '#111a2b', border: '1px solid rgba(255,255,255,.1)', color: '#f8fafc' }}
          />
          <Bar dataKey="balance" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs legacy-muted mt-2 border-t border-white/10 pt-2">
        Assumptions: {data.assumptions.join(" ")}
      </p>
    </div>
  );
}