import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import api from "../lib/api";
import BudgetProgress from "./BudgetProgress";
import { currentMonth } from "../lib/utils";
import type { BudgetSummary } from "../types";

const fetchBudgetSummary = async (): Promise<BudgetSummary[]> => {
  const { data } = await api.get(`/budgets/summary?month=${currentMonth()}`);
  return data;
};

export function DashboardBudgets() {
  const { data: summary, isLoading } = useQuery<BudgetSummary[]>({
    queryKey: ["budget-summary", currentMonth()],
    queryFn: fetchBudgetSummary,
  });

  return (
    <div className="legacy-dark-card p-5 rounded-2xl border shadow-xl shadow-black/10 h-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold tracking-tight">Monthly Budgets</h2>
        <Link to="/budgets" className="text-sm text-blue-600 hover:underline flex items-center">
          View All <ArrowRight className="h-4 w-4 ml-1" />
        </Link>
      </div>
      {isLoading ? (
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      ) : summary && summary.length > 0 ? (
        <BudgetProgress items={summary} />
      ) : (
        <p className="text-sm legacy-muted text-center py-8">No budgets set for this month.</p>
      )}
    </div>
  );
}