import type { BudgetSummary } from "../types";
import { formatINR } from "../lib/utils";

interface Props {
  items: BudgetSummary[];
}

export default function BudgetProgress({ items }: Props) {
  return (
    <div className="space-y-4">
      {items.map((item) => {
        const pct = Math.min(item.pct_used, 100);
        const over = item.pct_used > 100;
        const warn = item.pct_used >= 80 && !over;
        const barColor = over ? "bg-red-500" : warn ? "bg-yellow-400" : "bg-blue-500";

        return (
          <div key={item.category_name}>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-slate-200">{item.category_name}</span>
              <span className={over ? "text-red-600 font-semibold" : "text-slate-400"}>
                {formatINR(item.spent_amount)} / {formatINR(item.budget_amount)}
              </span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${barColor}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            {over && (
              <p className="text-xs text-red-500 mt-0.5">
                Over budget by {formatINR(Math.abs(item.remaining))}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
