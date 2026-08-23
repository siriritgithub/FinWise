import type { ReactNode } from "react";

interface Props {
  title: string;
  value: string;
  subtitle?: string;
  icon: ReactNode;
  color?: "blue" | "green" | "red" | "yellow";
}

const colorMap = {
  blue:   "bg-blue-50 text-blue-600",
  green:  "bg-green-50 text-green-600",
  red:    "bg-red-50 text-red-600",
  yellow: "bg-yellow-50 text-yellow-600",
};

export default function StatCard({ title, value, subtitle, icon, color = "blue" }: Props) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`p-3 rounded-lg ${colorMap[color]}`}>{icon}</div>
      <div>
        <p className="text-sm text-slate-400">{title}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}
