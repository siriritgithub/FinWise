import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  LineChart,
  Line,
} from "recharts";
import api from "../lib/api";
import { formatINR } from "../lib/utils";
import type {
  HealthScore,
  Anomaly,
  SpendingTrend,
} from "../types";
import {
  HeartPulse,
  ShieldAlert,
  Wallet,
  PiggyBank,
  Sparkles,
  Download,
  Calculator,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Info,
  XCircle,
  Lightbulb,
  Target,
  CalendarDays,
  CircleDollarSign,
} from "lucide-react";

/* =========================================================
   CONSTANTS
========================================================= */

const PIE_COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
  "#f97316",
];

/* =========================================================
   FORECAST TYPES
========================================================= */

interface ForecastItem {
  date: string;
  predicted_balance: number | string;
  is_low_balance?: boolean;
  status?: string;
  events?: string[];
  event_details?: any[];
}

interface ForecastResponse {
  days: number;
  forecast: ForecastItem[];
  assumptions: string[];
  current_balance: number | string;

  expected_income?: number | string;
  expected_expenses?: number | string;
  net_cash_flow?: number | string;
  projected_ending_balance?: number | string;
  lowest_projected_balance?: number | string;
  lowest_balance_date?: string;
  overall_status?: string;
  upcoming_events?: any[];
}

/* =========================================================
   AI INSIGHT TYPES
========================================================= */

interface FinancialInsight {
  type: string;
  priority: string;
  title: string;
  message: string;
}

interface InsightsResponse {
  generated_for: string;

  summary: {
    current_balance: number;
    monthly_income: number;
    monthly_expenses: number;
    monthly_savings: number;
    savings_rate: number;
    income_change_pct: number;
    expense_change_pct: number;
    projected_ending_balance: number;
    lowest_projected_balance: number;
    emergency_months: number;
    anomaly_count: number;
  };

  top_spending_categories: {
    category: string;
    total_90_days: number;
    average_monthly: number;
  }[];

  insights: FinancialInsight[];

  recommended_actions: string[];
}

/* =========================================================
   BUDGET TYPES
========================================================= */

interface BudgetRecommendation {
  category: string;

  average_monthly: number | string;

  recommended_budget: number | string;

  buffer?: number | string;

  reason?: string;

  total_90_days?: number | string;

  current_month_spending?: number | string;

  budget_used_pct?: number | string;

  remaining_budget?: number | string;

  projected_monthly_spending?: number | string;

  status?:
    | "under_budget"
    | "near_limit"
    | "over_budget"
    | "projected_over_budget"
    | string;
}

/* =========================================================
   SMART SAVINGS PLAN TYPES
========================================================= */

interface SavingsPlanGoal {
  id: number;

  name: string;

  priority?: string;

  target_amount: number | string;

  current_amount: number | string;

  remaining_amount: number | string;

  deadline?: string | null;

  days_remaining?: number;

  required_by_deadline?: number | string;

  required_monthly?: number | string;

  required_monthly_equivalent?: number | string;
}

interface SavingsPlanResponse {
  generated_for: string;

  financial_status: string;

  monthly_income: number | string;

  average_monthly_income: number | string;

  monthly_expenses: number | string;

  average_monthly_expenses: number | string;

  monthly_surplus: number | string;

  historical_surplus: number | string;

  current_month_income: number | string;

  current_month_expenses: number | string;

  current_month_savings: number | string;

  projected_current_month_expenses: number | string;

  current_balance: number | string;

  recommended_savings: number | string;

  savings_rate: number | string;

  safe_to_spend: number | string;

  required_goal_contribution: number | string;

  goal_amount_required_by_deadlines?: number | string;

  available_after_goals: number | string;

  goal_pressure: number | string;

  goals: SavingsPlanGoal[];

  recommendations: string[];
}

/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function Analytics() {
  /* =======================================================
     ANALYTICS API QUERIES
  ======================================================= */

  const {
    data: health,
    isLoading: healthLoading,
  } = useQuery<HealthScore>({
    queryKey: ["health-score"],
    queryFn: () =>
      api
        .get("/analytics/health-score")
        .then((r) => r.data),
  });

  const {
    data: anomalies = [],
    isLoading: anomaliesLoading,
  } = useQuery<Anomaly[]>({
    queryKey: ["anomalies"],
    queryFn: () =>
      api
        .get("/analytics/anomalies?days=90")
        .then((r) => r.data),
  });

  const {
    data: trends = [],
    isLoading: trendsLoading,
  } = useQuery<SpendingTrend[]>({
    queryKey: ["spending-trends"],
    queryFn: () =>
      api
        .get("/analytics/spending-trends?months=6")
        .then((r) => r.data),
  });

  const { data: net } = useQuery<any>({
    queryKey: ["net-worth"],
    queryFn: () =>
      api
        .get("/analytics/net-worth")
        .then((r) => r.data),
  });

  const { data: emergency } = useQuery<any>({
    queryKey: ["emergency-fund"],
    queryFn: () =>
      api
        .get("/analytics/emergency-fund")
        .then((r) => r.data),
  });

  const {
    data: recommendations = [],
    isLoading: recommendationsLoading,
  } = useQuery<BudgetRecommendation[]>({
    queryKey: ["budget-recommendations"],
    queryFn: () =>
      api
        .get("/analytics/budget-recommendations")
        .then((r) => r.data),
  });

  const {
    data: report,
    isLoading: reportLoading,
  } = useQuery<any>({
    queryKey: ["monthly-report"],
    queryFn: () =>
      api
        .get("/analytics/monthly-report")
        .then((r) => r.data),
  });

  /* =======================================================
     CASH FLOW
  ======================================================= */

  const {
    data: forecast,
    isLoading: forecastLoading,
    error: forecastError,
  } = useQuery<ForecastResponse>({
    queryKey: ["cashflow"],
    queryFn: () =>
      api
        .get("/analytics/cashflow?days=30")
        .then((r) => r.data),
  });

  /* =======================================================
     AI FINANCIAL INSIGHTS
  ======================================================= */

  const {
    data: insightsData,
    isLoading: insightsLoading,
    error: insightsError,
  } = useQuery<InsightsResponse>({
    queryKey: ["financial-insights"],
    queryFn: () =>
      api
        .get("/analytics/insights")
        .then((r) => r.data),
  });

  /* =======================================================
     SMART SAVINGS PLAN
  ======================================================= */

  const {
    data: savingsPlan,
    isLoading: savingsPlanLoading,
    error: savingsPlanError,
  } = useQuery<SavingsPlanResponse>({
    queryKey: ["savings-plan"],
    queryFn: () =>
      api
        .get("/analytics/savings-plan")
        .then((r) => r.data),
  });

  /* =======================================================
     SPENDING CATEGORY DATA
  ======================================================= */

  const cats: Record<string, number> = {};

  trends.forEach((t) => {
    const category =
      t.category_name || "Other";

    cats[category] =
      (cats[category] || 0) +
      Number(t.total_spent || 0);
  });

  const pieData = Object.entries(cats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 7)
    .map(([name, value]) => ({
      name,
      value,
    }));

  /* =======================================================
     MONTHLY SPENDING DATA
  ======================================================= */

  const monthTotals: Record<string, number> = {};

  trends.forEach((t) => {
    monthTotals[t.month] =
      (monthTotals[t.month] || 0) +
      Number(t.total_spent || 0);
  });

  const barData = Object.entries(monthTotals)
    .sort()
    .map(([month, total]) => ({
      month,
      total,
    }));

  /* =======================================================
     FORECAST DATA
  ======================================================= */

  const forecastData =
    forecast?.forecast?.map((item) => {
      const parsedDate =
        new Date(item.date);

      return {
        ...item,

        balance: Number(
          item.predicted_balance || 0
        ),

        displayDate:
          parsedDate.toLocaleDateString(
            "en-GB",
            {
              day: "2-digit",
              month: "short",
            }
          ),

        eventText:
          item.events &&
          item.events.length > 0
            ? item.events.join(", ")
            : "No scheduled events",
      };
    }) || [];

  /* =======================================================
     FORECAST RANGE
  ======================================================= */

  const forecastBalances =
    forecastData.map(
      (item) => item.balance
    );

  const minForecastBalance =
    forecastBalances.length > 0
      ? Math.min(...forecastBalances)
      : 0;

  const maxForecastBalance =
    forecastBalances.length > 0
      ? Math.max(...forecastBalances)
      : 0;

  const forecastPadding =
    Math.max(
      (maxForecastBalance -
        minForecastBalance) *
        0.2,
      100
    );

  const forecastDomainMin =
    Math.max(
      0,
      minForecastBalance -
        forecastPadding
    );

  const forecastDomainMax =
    maxForecastBalance +
    forecastPadding;

  /* =======================================================
     LOW BALANCE DAYS
  ======================================================= */

  const lowBalanceDays =
    forecastData.filter(
      (item) =>
        item.is_low_balance
    );

  /* =======================================================
     HEALTH SCORE COLORS
  ======================================================= */

  const gradeColor: Record<
    string,
    string
  > = {
    A: "text-emerald-400",
    B: "text-blue-400",
    C: "text-amber-400",
    D: "text-orange-400",
    F: "text-red-400",
  };

  /* =======================================================
     INSIGHT HELPERS
  ======================================================= */

  const getInsightIcon = (
    insight: FinancialInsight
  ) => {
    if (
      insight.type === "positive"
    ) {
      return (
        <CheckCircle2
          size={19}
          className="text-emerald-400"
        />
      );
    }

    if (
      insight.type === "warning"
    ) {
      return (
        <AlertTriangle
          size={19}
          className="text-amber-400"
        />
      );
    }

    if (
      insight.type === "critical"
    ) {
      return (
        <XCircle
          size={19}
          className="text-rose-400"
        />
      );
    }

    return (
      <Info
        size={19}
        className="text-blue-400"
      />
    );
  };

  const getInsightContainer = (
    insight: FinancialInsight
  ) => {
    if (
      insight.priority === "high" ||
      insight.type === "warning" ||
      insight.type === "critical"
    ) {
      return "border-amber-500/20 bg-amber-500/5";
    }

    if (
      insight.type === "positive"
    ) {
      return "border-emerald-500/20 bg-emerald-500/5";
    }

    return "border-blue-500/20 bg-blue-500/5";
  };

  /* =======================================================
     BUDGET HELPERS
  ======================================================= */

  const budgetStats =
    recommendations.reduce(
      (stats, recommendation) => {
        const status =
          recommendation.status ||
          "under_budget";

        if (
          status === "over_budget" ||
          status ===
            "projected_over_budget"
        ) {
          stats.over += 1;
        } else if (
          status === "near_limit"
        ) {
          stats.near += 1;
        } else {
          stats.under += 1;
        }

        return stats;
      },
      {
        under: 0,
        near: 0,
        over: 0,
      }
    );

  const getBudgetStatus = (
    recommendation: BudgetRecommendation
  ) => {
    const status =
      recommendation.status ||
      "under_budget";

    if (
      status === "over_budget"
    ) {
      return {
        label: "Over budget",
        className:
          "text-rose-400 bg-rose-500/10 border-rose-500/20",
        icon: (
          <XCircle size={14} />
        ),
      };
    }

    if (
      status ===
      "projected_over_budget"
    ) {
      return {
        label:
          "Projected over budget",
        className:
          "text-amber-400 bg-amber-500/10 border-amber-500/20",
        icon: (
          <TrendingUp size={14} />
        ),
      };
    }

    if (
      status === "near_limit"
    ) {
      return {
        label: "Near limit",
        className:
          "text-amber-400 bg-amber-500/10 border-amber-500/20",
        icon: (
          <AlertTriangle
            size={14}
          />
        ),
      };
    }

    return {
      label: "Under budget",
      className:
        "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      icon: (
        <CheckCircle2
          size={14}
        />
      ),
    };
  };

  const getBudgetProgress = (
    recommendation: BudgetRecommendation
  ) => {
    const used = Number(
      recommendation.budget_used_pct ||
        0
    );

    return Math.min(
      Math.max(used, 0),
      100
    );
  };

  /* =======================================================
     SMART SAVINGS HELPERS
  ======================================================= */

  const savingsStatus =
    savingsPlan?.financial_status ||
    "unknown";

  const savingsStatusConfig: Record<
    string,
    {
      label: string;
      className: string;
    }
  > = {
    healthy: {
      label: "Healthy",
      className:
        "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },

    on_track: {
      label: "On track",
      className:
        "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },

    goal_pressure: {
      label: "Goal pressure",
      className:
        "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },

    caution: {
      label: "Caution",
      className:
        "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },

    critical: {
      label: "Critical",
      className:
        "text-rose-400 bg-rose-500/10 border-rose-500/20",
    },

    unknown: {
      label: "Unavailable",
      className:
        "text-slate-400 bg-slate-500/10 border-slate-500/20",
    },
  };

  const savingsStatusInfo =
    savingsStatusConfig[
      savingsStatus
    ] ||
    savingsStatusConfig.unknown;

  const savingsGoalRequired =
    Number(
      savingsPlan?.goal_amount_required_by_deadlines ??
        savingsPlan?.goals?.reduce(
          (sum, goal) =>
            sum +
            Number(
              goal.required_by_deadline ||
                0
            ),
          0
        ) ??
        0
    );

  const savingsProgress =
    savingsPlan &&
    Number(
      savingsPlan.monthly_income ||
        0
    ) > 0
      ? Math.min(
          Math.max(
            (Number(
              savingsPlan.recommended_savings ||
                0
            ) /
              Number(
                savingsPlan.monthly_income ||
                  1
              )) *
              100,
            0
          ),
          100
        )
      : 0;

  const goalPressure =
    Number(
      savingsPlan?.goal_pressure ||
        0
    );

  /* =======================================================
     DOWNLOAD REPORT
  ======================================================= */

  const downloadReport = () => {
    if (!report) return;

    const text = `FinWise Monthly Report

Month: ${report.month}

Income: INR ${report.income}

Expenses: INR ${report.expenses}

Savings: INR ${report.savings}

Savings rate: ${report.savings_rate}%

Expense change: ${report.expense_change_pct}%
`;

    const blob = new Blob(
      [text],
      {
        type: "text/plain",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const a =
      document.createElement("a");

    a.href = url;

    a.download =
      `finwise-report-${report.month}.txt`;

    document.body.appendChild(a);

    a.click();

    document.body.removeChild(a);

    URL.revokeObjectURL(url);
  };

  /* =======================================================
     LOADING
  ======================================================= */

  const analyticsLoading =
    healthLoading ||
    anomaliesLoading ||
    trendsLoading ||
    recommendationsLoading ||
    reportLoading ||
    savingsPlanLoading;
  void analyticsLoading;

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="space-y-6 page-shell">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">

        <div>

          <p className="text-sm font-semibold text-blue-400">
            Financial intelligence
          </p>

          <h1 className="text-3xl font-black text-white">
            Analytics & Insights
          </h1>

          <p className="text-sm text-slate-400 mt-1">
            Understand, predict and improve
            your financial behavior.
          </p>

        </div>

        <button
          onClick={downloadReport}
          disabled={!report}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-[#111a2b] px-4 py-2.5 text-sm font-bold text-slate-200 hover:bg-white/5 disabled:opacity-50 transition-colors"
        >
          <Download size={16} />
          Export monthly report
        </button>

      </div>

      {/* =====================================================
          TOP METRIC CARDS
      ===================================================== */}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

        {/* NET WORTH */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-blue-500/10 text-blue-400 ring-1 ring-blue-400/15 flex items-center justify-center">
              <Wallet size={21} />
            </div>

            <div>

              <p className="text-xs text-slate-400">
                Net worth
              </p>

              <p className="text-2xl font-black text-white">
                {formatINR(
                  net?.net_worth || 0
                )}
              </p>

            </div>

          </div>

          <p className="text-xs text-slate-400 mt-3">
            Assets{" "}
            {formatINR(
              net?.assets || 0
            )}
            {" · "}
            Liabilities{" "}
            {formatINR(
              net?.liabilities || 0
            )}
          </p>

        </div>

        {/* HEALTH SCORE */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-400/15 flex items-center justify-center">
              <HeartPulse size={21} />
            </div>

            <div>

              <p className="text-xs text-slate-400">
                Health score
              </p>

              <p
                className={`text-2xl font-black ${
                  gradeColor[
                    health?.grade ||
                      "F"
                  ]
                }`}
              >
                {health?.total_score?.toFixed(
                  0
                ) ?? "—"}

                <span className="text-sm text-slate-500">
                  /100
                </span>
              </p>

            </div>

          </div>

          <p className="text-xs text-slate-400 mt-3">
            Grade{" "}
            {health?.grade || "—"}
          </p>

        </div>

        {/* ANOMALIES */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-amber-500/10 text-amber-400 ring-1 ring-amber-400/15 flex items-center justify-center">
              <ShieldAlert size={21} />
            </div>

            <div>

              <p className="text-xs text-slate-400">
                Anomalies
              </p>

              <p className="text-2xl font-black text-white">
                {anomalies.length}
              </p>

            </div>

          </div>

          <p className="text-xs text-slate-400 mt-3">
            Last 90 days · review flags
          </p>

        </div>

        {/* EMERGENCY FUND */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-violet-500/10 text-violet-400 ring-1 ring-violet-400/15 flex items-center justify-center">
              <PiggyBank size={21} />
            </div>

            <div>

              <p className="text-xs text-slate-400">
                Emergency cover
              </p>

              <p className="text-2xl font-black text-white">
                {emergency?.months_covered?.toFixed(
                  1
                ) ?? "0.0"}{" "}
                mo
              </p>

            </div>

          </div>

          <p className="text-xs text-slate-400 mt-3">
            3–6 months is a common planning range
          </p>

        </div>

      </div>

      {/* =====================================================
          AI FINANCIAL INSIGHTS
      ===================================================== */}

      <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-5">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-blue-500/10 text-blue-400 ring-1 ring-blue-400/15 flex items-center justify-center">
              <Sparkles size={21} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                AI Financial Insights
              </h2>

              <p className="text-xs text-slate-400 mt-0.5">
                Personalized observations based on your FinWise data
              </p>

            </div>

          </div>

          {insightsData && (
            <span className="text-[11px] text-slate-500">
              Generated{" "}
              {new Date(
                insightsData.generated_for
              ).toLocaleDateString(
                "en-GB"
              )}
            </span>
          )}

        </div>

        {insightsLoading && (
          <div className="grid md:grid-cols-2 gap-3">

            {[1, 2, 3, 4].map(
              (item) => (
                <div
                  key={item}
                  className="rounded-xl border border-white/5 bg-slate-900/50 p-4 animate-pulse"
                >
                  <div className="h-4 w-40 bg-slate-800 rounded mb-3" />
                  <div className="h-3 w-full bg-slate-800 rounded mb-2" />
                  <div className="h-3 w-4/5 bg-slate-800 rounded" />
                </div>
              )
            )}

          </div>
        )}

        {!insightsLoading &&
          insightsError && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">

              <div className="flex items-center gap-2 text-amber-400">

                <AlertTriangle size={18} />

                <p className="font-semibold text-sm">
                  Insights unavailable
                </p>

              </div>

              <p className="text-xs text-slate-400 mt-1">
                We couldn't load your financial insights right now.
                Your other analytics are still available.
              </p>

            </div>
          )}

        {!insightsLoading &&
          !insightsError &&
          insightsData &&
          insightsData.insights.length >
            0 && (

            <div className="grid md:grid-cols-2 gap-3">

              {insightsData.insights.map(
                (
                  insight,
                  index
                ) => (

                  <div
                    key={`${insight.title}-${index}`}
                    className={`rounded-xl border p-4 transition-all hover:bg-white/[0.02] ${getInsightContainer(
                      insight
                    )}`}
                  >

                    <div className="flex items-start gap-3">

                      <div className="mt-0.5 shrink-0">
                        {getInsightIcon(
                          insight
                        )}
                      </div>

                      <div className="min-w-0">

                        <div className="flex flex-wrap items-center gap-2">

                          <p className="font-semibold text-slate-100">
                            {insight.title}
                          </p>

                          <span className="text-[9px] uppercase tracking-wider font-bold text-slate-500">
                            {insight.priority}
                          </span>

                        </div>

                        <p className="text-xs text-slate-400 leading-5 mt-1">
                          {insight.message}
                        </p>

                      </div>

                    </div>

                  </div>

                )
              )}

            </div>
          )}

        {!insightsLoading &&
          !insightsError &&
          insightsData &&
          insightsData.recommended_actions
            .length > 0 && (

            <div className="mt-5 border-t border-white/10 pt-5">

              <div className="flex items-center gap-2 mb-3">

                <Lightbulb
                  size={17}
                  className="text-blue-400"
                />

                <h3 className="text-sm font-bold text-white">
                  Recommended actions
                </h3>

              </div>

              <div className="grid md:grid-cols-2 gap-3">

                {insightsData.recommended_actions.map(
                  (
                    action,
                    index
                  ) => (

                    <div
                      key={index}
                      className="flex items-start gap-3 rounded-xl bg-slate-900/60 border border-white/5 p-3"
                    >

                      <span className="h-6 w-6 shrink-0 rounded-full bg-blue-500/10 text-blue-400 text-[11px] font-bold flex items-center justify-center">
                        {index + 1}
                      </span>

                      <p className="text-xs text-slate-400 leading-5">
                        {action}
                      </p>

                    </div>

                  )
                )}

              </div>

            </div>

          )}

      </div>

      {/* =====================================================
          SMART SAVINGS PLAN
      ===================================================== */}

      <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-400/15 flex items-center justify-center">
              <Target size={21} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Smart Savings Plan
              </h2>

              <p className="text-xs text-slate-400 mt-0.5">
                Savings capacity, goal deadlines and safe spending
              </p>

            </div>

          </div>

          {savingsPlan && (
            <div className="flex items-center gap-2">

              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-wide font-black ${savingsStatusInfo.className}`}
              >
                {savingsStatusInfo.label}
              </span>

              <span className="text-[11px] text-slate-500">
                {new Date(
                  savingsPlan.generated_for
                ).toLocaleDateString(
                  "en-GB"
                )}
              </span>

            </div>
          )}

        </div>

        {/* LOADING */}

        {savingsPlanLoading && (
          <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">

            {[1, 2, 3, 4].map(
              (item) => (

                <div
                  key={item}
                  className="rounded-xl border border-white/5 bg-slate-900/50 p-4 animate-pulse"
                >

                  <div className="h-3 w-24 bg-slate-800 rounded mb-3" />

                  <div className="h-6 w-32 bg-slate-800 rounded" />

                </div>

              )
            )}

          </div>
        )}

        {/* ERROR */}

        {!savingsPlanLoading &&
          savingsPlanError && (

            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">

              <div className="flex items-center gap-2 text-amber-400">

                <AlertTriangle size={18} />

                <p className="font-semibold text-sm">
                  Savings plan unavailable
                </p>

              </div>

              <p className="text-xs text-slate-400 mt-1">
                We couldn't load your savings plan right now.
                Your other analytics are still available.
              </p>

            </div>

          )}

        {/* DATA */}

        {!savingsPlanLoading &&
          !savingsPlanError &&
          savingsPlan && (

            <>

              {/* SUMMARY CARDS */}

              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">

                {/* RECOMMENDED SAVINGS */}

                <div className="rounded-xl bg-slate-900/60 border border-white/5 p-4">

                  <div className="flex items-center justify-between">

                    <p className="text-[11px] text-slate-500">
                      Recommended savings
                    </p>

                    <PiggyBank
                      size={15}
                      className="text-emerald-400"
                    />

                  </div>

                  <p className="text-xl font-black text-emerald-400 mt-2">
                    {formatINR(
                      Number(
                        savingsPlan.recommended_savings ||
                          0
                      )
                    )}
                  </p>

                  <p className="text-[10px] text-slate-500 mt-1">
                    {Number(
                      savingsPlan.savings_rate ||
                        0
                    ).toFixed(1)}
                    % of monthly income
                  </p>

                </div>

                {/* SAFE TO SPEND */}

                <div className="rounded-xl bg-slate-900/60 border border-white/5 p-4">

                  <div className="flex items-center justify-between">

                    <p className="text-[11px] text-slate-500">
                      Safe to spend
                    </p>

                    <CircleDollarSign
                      size={15}
                      className="text-blue-400"
                    />

                  </div>

                  <p className="text-xl font-black text-blue-400 mt-2">
                    {formatINR(
                      Number(
                        savingsPlan.safe_to_spend ||
                          0
                      )
                    )}
                  </p>

                  <p className="text-[10px] text-slate-500 mt-1">
                    Flexible monthly spending
                  </p>

                </div>

                {/* GOAL COMMITMENT */}

                <div className="rounded-xl bg-slate-900/60 border border-white/5 p-4">

                  <div className="flex items-center justify-between">

                    <p className="text-[11px] text-slate-500">
                      Goal commitment
                    </p>

                    <Target
                      size={15}
                      className="text-amber-400"
                    />

                  </div>

                  <p className="text-xl font-black text-amber-400 mt-2">
                    {formatINR(
                      Number(
                        savingsPlan.required_goal_contribution ||
                          0
                      )
                    )}
                  </p>

                  <p className="text-[10px] text-slate-500 mt-1">
                    Monthly-equivalent pace
                  </p>

                </div>

                {/* CURRENT SURPLUS */}

                <div className="rounded-xl bg-slate-900/60 border border-white/5 p-4">

                  <div className="flex items-center justify-between">

                    <p className="text-[11px] text-slate-500">
                      Current surplus
                    </p>

                    <TrendingUp
                      size={15}
                      className="text-emerald-400"
                    />

                  </div>

                  <p className="text-xl font-black text-white mt-2">
                    {formatINR(
                      Number(
                        savingsPlan.monthly_surplus ||
                          0
                      )
                    )}
                  </p>

                  <p className="text-[10px] text-slate-500 mt-1">
                    Monthly income minus expenses
                  </p>

                </div>

              </div>

              {/* SAVINGS CAPACITY */}

              <div className="mt-4 rounded-xl border border-white/5 bg-slate-900/40 p-4">

                <div className="flex items-center justify-between mb-2">

                  <div>

                    <p className="text-xs font-semibold text-slate-300">
                      Recommended savings capacity
                    </p>

                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Based on your current monthly income
                    </p>

                  </div>

                  <span className="text-xs font-black text-emerald-400">
                    {savingsProgress.toFixed(1)}%
                  </span>

                </div>

                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">

                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{
                      width: `${savingsProgress}%`,
                    }}
                  />

                </div>

                <div className="flex justify-between mt-2 text-[10px]">

                  <span className="text-slate-500">
                    Income{" "}
                    {formatINR(
                      Number(
                        savingsPlan.monthly_income ||
                          0
                      )
                    )}
                  </span>

                  <span className="text-slate-400">
                    Save{" "}
                    {formatINR(
                      Number(
                        savingsPlan.recommended_savings ||
                          0
                      )
                    )}
                  </span>

                </div>

              </div>

              {/* GOAL PRESSURE */}

              {goalPressure > 0 && (

                <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">

                  <div className="flex items-start gap-3">

                    <AlertTriangle
                      size={18}
                      className="text-amber-400 mt-0.5 shrink-0"
                    />

                    <div>

                      <p className="text-sm font-semibold text-amber-300">
                        Your goals are putting pressure on cash flow
                      </p>

                      <p className="text-xs text-slate-400 mt-1 leading-5">

                        Goal commitments are approximately{" "}

                        <span className="font-bold text-amber-300">
                          {formatINR(
                            goalPressure
                          )}
                        </span>{" "}

                        above your safer savings amount.
                        Consider reducing discretionary spending,
                        increasing income, or extending a deadline.

                      </p>

                    </div>

                  </div>

                </div>

              )}

              {/* ACTIVE GOALS */}

              {savingsPlan.goals.length >
                0 && (

                <div className="mt-5">

                  <div className="flex items-center justify-between mb-3">

                    <div>

                      <h3 className="text-sm font-bold text-white">
                        Active goal plan
                      </h3>

                      <p className="text-[10px] text-slate-500 mt-0.5">
                        Funding required for your current deadlines
                      </p>

                    </div>

                    <span className="text-[10px] text-slate-500">
                      {savingsPlan.goals.length} goal
                      {savingsPlan.goals.length !== 1
                        ? "s"
                        : ""}
                    </span>

                  </div>

                  <div className="space-y-3">

                    {savingsPlan.goals.map(
                      (goal) => {

                        const current =
                          Number(
                            goal.current_amount ?? 0
                          );

                        const remaining =
                          Number(
                            goal.remaining_amount ?? 0
                          );

                        // The savings-plan API may return a stale/incorrect
                        // target_amount. For the UI, the authoritative target
                        // is current amount + remaining amount.
                        const target =
                          remaining >= 0
                            ? current + remaining
                            : Number(
                                goal.target_amount ?? 0
                              );

                        const progress =
                          target > 0
                            ? Math.min(
                                Math.max(
                                  (current /
                                    target) *
                                    100,
                                  0
                                ),
                                100
                              )
                            : 0;

                        const requiredByDeadline =
                          Number(
                            goal.required_by_deadline ??
                              remaining ??
                              0
                          );

                        const requiredMonthly =
                          Number(
                            goal.required_monthly ??
                              goal.required_monthly_equivalent ??
                              0
                          );

                        return (

                          <div
                            key={goal.id}
                            className="rounded-xl border border-white/5 bg-slate-900/60 p-4"
                          >

                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">

                              <div className="min-w-0">

                                <div className="flex flex-wrap items-center gap-2">

                                  <p className="font-semibold text-white">
                                    {goal.name}
                                  </p>

                                  {goal.priority && (

                                    <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[9px] uppercase tracking-wide font-bold text-slate-400">
                                      {goal.priority}
                                    </span>

                                  )}

                                </div>

                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">

                                  {goal.deadline && (

                                    <span className="inline-flex items-center gap-1 text-[10px] text-slate-500">

                                      <CalendarDays
                                        size={12}
                                      />

                                      {new Date(
                                        goal.deadline
                                      ).toLocaleDateString(
                                        "en-GB",
                                        {
                                          day: "2-digit",
                                          month: "short",
                                          year: "numeric",
                                        }
                                      )}

                                    </span>

                                  )}

                                  {goal.days_remaining !==
                                    undefined && (

                                    <span
                                      className={`text-[10px] font-semibold ${
                                        goal.days_remaining <=
                                        7
                                          ? "text-rose-400"
                                          : goal.days_remaining <=
                                            30
                                          ? "text-amber-400"
                                          : "text-slate-500"
                                      }`}
                                    >
                                      {goal.days_remaining} day
                                      {goal.days_remaining !==
                                      1
                                        ? "s"
                                        : ""}{" "}
                                      left
                                    </span>

                                  )}

                                </div>

                              </div>

                              <div className="text-left sm:text-right">

                                <p className="text-xs font-black text-white">

                                  {formatINR(
                                    current
                                  )}
                                  {" / "}
                                  {formatINR(
                                    target
                                  )}

                                </p>

                                <p className="text-[10px] text-slate-500 mt-0.5">
                                  {progress.toFixed(
                                    1
                                  )}
                                  % funded
                                </p>

                              </div>

                            </div>

                            {/* GOAL PROGRESS */}

                            <div className="h-2 bg-slate-800 rounded-full overflow-hidden mt-3">

                              <div
                                className="h-full bg-blue-500 rounded-full transition-all"
                                style={{
                                  width: `${progress}%`,
                                }}
                              />

                            </div>

                            {/* GOAL DETAILS */}

                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">

                              <div>

                                <p className="text-[10px] text-slate-500">
                                  Remaining
                                </p>

                                <p className="text-sm font-bold text-slate-200 mt-0.5">
                                  {formatINR(
                                    Number(
                                      goal.remaining_amount ||
                                        0
                                    )
                                  )}
                                </p>

                              </div>

                              <div>

                                <p className="text-[10px] text-slate-500">
                                  Needed by deadline
                                </p>

                                <p className="text-sm font-bold text-amber-400 mt-0.5">
                                  {formatINR(
                                    requiredByDeadline
                                  )}
                                </p>

                              </div>

                              <div>

                                <p className="text-[10px] text-slate-500">
                                  Monthly equivalent
                                </p>

                                <p className="text-sm font-bold text-blue-400 mt-0.5">
                                  {formatINR(
                                    requiredMonthly
                                  )}
                                </p>

                              </div>

                            </div>

                          </div>

                        );
                      }
                    )}

                  </div>

                  <div className="mt-3 flex items-center justify-between rounded-xl border border-white/5 bg-slate-950/30 px-3 py-2.5">

                    <span className="text-[10px] text-slate-500">
                      Total required across goal deadlines
                    </span>

                    <span className="text-xs font-black text-amber-400">
                      {formatINR(
                        savingsGoalRequired
                      )}
                    </span>

                  </div>

                </div>

              )}

              {/* NO GOALS */}

              {savingsPlan.goals.length ===
                0 && (

                <div className="mt-5 rounded-xl border border-white/5 bg-slate-900/40 p-4">

                  <div className="flex items-center gap-2">

                    <CheckCircle2
                      size={17}
                      className="text-emerald-400"
                    />

                    <p className="text-sm font-semibold text-slate-200">
                      No active goal deadlines need funding right now.
                    </p>

                  </div>

                </div>

              )}

              {/* SAVINGS RECOMMENDATIONS */}

              {savingsPlan.recommendations.length >
                0 && (

                <div className="mt-5 border-t border-white/10 pt-5">

                  <div className="flex items-center gap-2 mb-3">

                    <Lightbulb
                      size={17}
                      className="text-blue-400"
                    />

                    <h3 className="text-sm font-bold text-white">
                      Savings recommendations
                    </h3>

                  </div>

                  <div className="grid md:grid-cols-2 gap-3">

                    {savingsPlan.recommendations.map(
                      (
                        recommendation,
                        index
                      ) => (

                        <div
                          key={`${recommendation}-${index}`}
                          className="flex items-start gap-3 rounded-xl bg-slate-900/60 border border-white/5 p-3"
                        >

                          <span className="h-6 w-6 shrink-0 rounded-full bg-blue-500/10 text-blue-400 text-[11px] font-bold flex items-center justify-center">
                            {index + 1}
                          </span>

                          <p className="text-xs text-slate-400 leading-5">
                            {recommendation}
                          </p>

                        </div>

                      )
                    )}

                  </div>

                </div>

              )}

            </>

          )}

      </div>

      {/* =====================================================
          HEALTH + CASHFLOW
      ===================================================== */}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* FINANCIAL HEALTH */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <h2 className="font-bold text-white mb-5">
            Financial Health Score
          </h2>

          {health?.factors?.map(
            (factor) => {

              const percentage =
                factor.max_score > 0
                  ? (factor.score /
                      factor.max_score) *
                    100
                  : 0;

              return (

                <div
                  key={factor.name}
                  className="mb-5"
                >

                  <div className="flex justify-between text-sm text-slate-200">

                    <span>
                      {factor.name}
                    </span>

                    <span className="font-semibold">
                      {factor.score}/
                      {factor.max_score}
                    </span>

                  </div>

                  <div className="h-2 bg-slate-800 rounded-full mt-2 overflow-hidden">

                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{
                        width: `${percentage}%`,
                      }}
                    />

                  </div>

                  <p className="text-xs text-slate-400 mt-1.5">
                    {factor.description}
                  </p>

                  {factor.tip && (
                    <p className="text-xs text-amber-400 mt-1">
                      {factor.tip}
                    </p>
                  )}

                </div>

              );
            }
          )}

          <p className="text-[11px] text-slate-500 border-t border-white/10 pt-3">
            {health?.disclaimer}
          </p>

        </div>

        {/* CASHFLOW */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center justify-between">

            <div>

              <h2 className="font-bold text-white">
                Cash-flow forecast
              </h2>

              <p className="text-xs text-slate-400">
                Next{" "}
                {forecast?.days ||
                  30}{" "}
                days
              </p>

            </div>

            <Sparkles
              size={18}
              className="text-blue-400"
            />

          </div>

          {forecast && (

            <div className="grid grid-cols-2 gap-3 mt-4">

              <div className="rounded-xl bg-slate-900/60 border border-white/5 p-3">

                <p className="text-[11px] text-slate-500">
                  Current balance
                </p>

                <p className="text-lg font-black text-white mt-1">
                  {formatINR(
                    Number(
                      forecast.current_balance ||
                        0
                    )
                  )}
                </p>

              </div>

              <div className="rounded-xl bg-slate-900/60 border border-white/5 p-3">

                <p className="text-[11px] text-slate-500">
                  End forecast
                </p>

                <p
                  className={`text-lg font-black mt-1 ${
                    forecastData.length >
                      0 &&
                    forecastData[
                      forecastData.length -
                        1
                    ].balance <
                      Number(
                        forecast.current_balance ||
                          0
                      )
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {formatINR(
                    forecastData.length >
                      0
                      ? forecastData[
                          forecastData.length -
                            1
                        ].balance
                      : Number(
                          forecast.current_balance ||
                            0
                        )
                  )}
                </p>

              </div>

              <div className="rounded-xl bg-slate-900/60 border border-white/5 p-3">

                <p className="text-[11px] text-slate-500">
                  Expected income
                </p>

                <p className="text-lg font-black text-emerald-400 mt-1">
                  {formatINR(
                    Number(
                      forecast.expected_income ||
                        0
                    )
                  )}
                </p>

              </div>

              <div className="rounded-xl bg-slate-900/60 border border-white/5 p-3">

                <p className="text-[11px] text-slate-500">
                  Expected expenses
                </p>

                <p className="text-lg font-black text-rose-400 mt-1">
                  {formatINR(
                    Number(
                      forecast.expected_expenses ||
                        0
                    )
                  )}
                </p>

              </div>

            </div>

          )}

          {forecast && (

            <div className="mt-3 rounded-xl border border-white/5 bg-slate-900/40 p-3">

              <div className="flex items-center justify-between">

                <span className="text-xs text-slate-500">
                  30-day net cash flow
                </span>

                <span
                  className={`text-sm font-black ${
                    Number(
                      forecast.net_cash_flow ||
                        0
                    ) >= 0
                      ? "text-emerald-400"
                      : "text-rose-400"
                  }`}
                >
                  {Number(
                    forecast.net_cash_flow ||
                      0
                  ) >= 0
                    ? "+"
                    : ""}
                  {formatINR(
                    Number(
                      forecast.net_cash_flow ||
                        0
                    )
                  )}
                </span>

              </div>

            </div>

          )}

          {forecast &&
            forecast.lowest_projected_balance !==
              undefined && (

              <div className="mt-3 rounded-xl border border-white/5 bg-slate-900/40 p-3">

                <div className="flex items-center justify-between">

                  <span className="text-xs text-slate-500">
                    Lowest projected balance
                  </span>

                  <span
                    className={`text-sm font-black ${
                      Number(
                        forecast.lowest_projected_balance
                      ) < 3000
                        ? "text-rose-400"
                        : Number(
                            forecast.lowest_projected_balance
                          ) < 6000
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {formatINR(
                      Number(
                        forecast.lowest_projected_balance
                      )
                    )}
                  </span>

                </div>

                {forecast.lowest_balance_date && (

                  <p className="text-[10px] text-slate-500 mt-1">
                    Expected on{" "}
                    {new Date(
                      forecast.lowest_balance_date
                    ).toLocaleDateString(
                      "en-GB"
                    )}
                  </p>

                )}

              </div>

            )}

          {forecast?.overall_status && (

            <div className="mt-3 flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/40 p-3">

              <span className="text-xs text-slate-500">
                Forecast status
              </span>

              <span
                className={`text-xs font-black uppercase ${
                  forecast.overall_status ===
                  "safe"
                    ? "text-emerald-400"
                    : forecast.overall_status ===
                      "caution"
                    ? "text-amber-400"
                    : "text-rose-400"
                }`}
              >
                {forecast.overall_status}
              </span>

            </div>

          )}

          {forecastLoading && (

            <div className="h-[260px] flex items-center justify-center text-slate-400">
              Loading forecast...
            </div>

          )}

          {forecastError && (

            <div className="h-[260px] flex items-center justify-center">

              <div className="text-center">

                <AlertTriangle
                  size={28}
                  className="mx-auto text-amber-400 mb-2"
                />

                <p className="text-sm text-slate-300">
                  Unable to load cash-flow forecast.
                </p>

              </div>

            </div>

          )}

          {!forecastLoading &&
            !forecastError &&
            forecastData.length >
              0 && (

              <div className="mt-4">

                <ResponsiveContainer
                  width="100%"
                  height={250}
                >

                  <LineChart
                    data={forecastData}
                    margin={{
                      top: 10,
                      right: 10,
                      left: -15,
                      bottom: 5,
                    }}
                  >

                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#26354d"
                    />

                    <XAxis
                      dataKey="displayDate"
                      tick={{
                        fontSize: 10,
                        fill: "#94a3b8",
                      }}
                      axisLine={{
                        stroke: "#334155",
                      }}
                      tickLine={{
                        stroke: "#334155",
                      }}
                      interval="preserveStartEnd"
                    />

                    <YAxis
                      domain={[
                        forecastDomainMin,
                        forecastDomainMax,
                      ]}
                      tick={{
                        fontSize: 10,
                        fill: "#94a3b8",
                      }}
                      axisLine={{
                        stroke: "#334155",
                      }}
                      tickLine={{
                        stroke: "#334155",
                      }}
                      tickFormatter={(value) =>
                        `₹${(
                          Number(value) /
                          1000
                        ).toFixed(0)}k`
                      }
                    />

                    <Tooltip
                      contentStyle={{
                        background:
                          "#111a2b",
                        border:
                          "1px solid rgba(255,255,255,.1)",
                        borderRadius:
                          "0.75rem",
                        color:
                          "#f8fafc",
                        fontSize: 12,
                      }}
                      labelStyle={{
                        color:
                          "#cbd5e1",
                        marginBottom:
                          4,
                      }}
                      formatter={(value: any) => [
                        formatINR(
                          Number(
                            value ?? 0
                          )
                        ),
                        "Predicted balance",
                      ]}
                      labelFormatter={(
                        _,
                        payload
                      ) => {
                        const item =
                          payload?.[0]
                            ?.payload;

                        return item?.eventText
                          ? `${item.displayDate} · ${item.eventText}`
                          : item?.displayDate ||
                              "";
                      }}
                    />

                    <Line
                      type="monotone"
                      dataKey="balance"
                      name="Predicted balance"
                      stroke="#3b82f6"
                      strokeWidth={3}
                      dot={false}
                      activeDot={{
                        r: 5,
                      }}
                    />

                  </LineChart>

                </ResponsiveContainer>

              </div>

            )}

          {lowBalanceDays.length >
            0 && (

            <div className="mt-3 rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">

              <div className="flex items-center gap-2 text-rose-300">

                <TrendingDown
                  size={15}
                />

                <p className="text-xs font-semibold">
                  Low balance warning
                </p>

              </div>

              <p className="text-[11px] text-slate-400 mt-1">
                Your forecast falls below the
                ₹3,000 safety threshold on{" "}
                {lowBalanceDays.length}{" "}
                day
                {lowBalanceDays.length >
                1
                  ? "s"
                  : ""}
                .
              </p>

            </div>

          )}

          {forecast?.upcoming_events &&
            forecast.upcoming_events
              .length > 0 && (

              <div className="mt-3 border-t border-white/10 pt-3">

                <p className="text-[11px] font-semibold text-slate-400 mb-2">
                  Upcoming events
                </p>

                <div className="space-y-2">

                  {forecast.upcoming_events
                    .slice(0, 5)
                    .map(
                      (
                        event: any,
                        index: number
                      ) => (

                        <div
                          key={index}
                          className="flex items-center justify-between rounded-lg bg-slate-900/50 px-3 py-2"
                        >

                          <div>

                            <p className="text-xs text-slate-300">
                              {event.label ||
                                event.description ||
                                event.name ||
                                "Scheduled event"}
                            </p>

                            {event.date && (

                              <p className="text-[10px] text-slate-500">
                                {new Date(
                                  event.date
                                ).toLocaleDateString(
                                  "en-GB"
                                )}
                              </p>

                            )}

                          </div>

                          {event.amount !==
                            undefined && (

                            <span
                              className={`text-xs font-bold ${
                                Number(
                                  event.amount
                                ) >= 0
                                  ? "text-emerald-400"
                                  : "text-rose-400"
                              }`}
                            >
                              {Number(
                                event.amount
                              ) >= 0
                                ? "+"
                                : ""}
                              {formatINR(
                                Number(
                                  event.amount
                                )
                              )}
                            </span>

                          )}

                        </div>

                      )
                    )}

                </div>

              </div>

            )}

          {forecast?.assumptions &&
            forecast.assumptions.length >
              0 && (

              <div className="mt-3 border-t border-white/10 pt-3">

                <p className="text-[11px] font-semibold text-slate-400 mb-1">
                  Forecast assumptions
                </p>

                <p className="text-[11px] text-slate-500 leading-5">
                  {forecast.assumptions.join(
                    " · "
                  )}
                </p>

              </div>

            )}

        </div>

      </div>

      {/* =====================================================
          SPENDING CHARTS
      ===================================================== */}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* MONTHLY SPENDING */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <h2 className="font-bold text-white mb-4">
            Monthly spending
          </h2>

          <ResponsiveContainer
            width="100%"
            height={230}
          >

            <BarChart
              data={barData}
            >

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#26354d"
              />

              <XAxis
                dataKey="month"
                tick={{
                  fontSize: 10,
                  fill: "#94a3b8",
                }}
              />

              <YAxis
                tick={{
                  fontSize: 10,
                  fill: "#94a3b8",
                }}
                tickFormatter={(value) =>
                  `₹${(
                    Number(value) /
                    1000
                  ).toFixed(0)}k`
                }
              />

              <Tooltip
                contentStyle={{
                  background:
                    "#111a2b",
                  border:
                    "1px solid rgba(255,255,255,.1)",
                  borderRadius:
                    "0.75rem",
                  color:
                    "#f8fafc",
                  fontSize: 12,
                }}
                formatter={(value: any) =>
                  formatINR(
                    Number(
                      value ?? 0
                    )
                  )
                }
              />

              <Bar
                dataKey="total"
                fill="#3b82f6"
                radius={[
                  5,
                  5,
                  0,
                  0,
                ]}
              />

            </BarChart>

          </ResponsiveContainer>

        </div>

        {/* CATEGORY SPENDING */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <h2 className="font-bold text-white mb-4">
            Spending by category
          </h2>

          {pieData.length > 0 ? (

            <ResponsiveContainer
              width="100%"
              height={230}
            >

              <PieChart>

                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={78}
                >

                  {pieData.map(
                    (_, index) => (

                      <Cell
                        key={index}
                        fill={
                          PIE_COLORS[
                            index %
                              PIE_COLORS.length
                          ]
                        }
                      />

                    )
                  )}

                </Pie>

                <Legend
                  iconSize={9}
                  wrapperStyle={{
                    fontSize: 11,
                    color: "#94a3b8",
                  }}
                />

                <Tooltip
                  contentStyle={{
                    background:
                      "#111a2b",
                    border:
                      "1px solid rgba(255,255,255,.1)",
                    borderRadius:
                      "0.75rem",
                    color:
                      "#f8fafc",
                    fontSize: 12,
                  }}
                  formatter={(value: any) =>
                    formatINR(
                      Number(
                        value ?? 0
                      )
                    )
                  }
                />

              </PieChart>

            </ResponsiveContainer>

          ) : (

            <div className="h-[230px] flex items-center justify-center text-sm text-slate-500">
              No spending category data available.
            </div>

          )}

        </div>

      </div>

      {/* =====================================================
          BUDGET RECOMMENDATIONS
      ===================================================== */}

      <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">

          <div className="flex items-center gap-2">

            <div className="h-10 w-10 rounded-xl bg-blue-500/10 text-blue-400 ring-1 ring-blue-400/15 flex items-center justify-center">
              <Calculator size={18} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Data-driven budget recommendations
              </h2>

              <p className="text-xs text-slate-400 mt-0.5">
                90-day spending history + 10% planning buffer
              </p>

            </div>

          </div>

          {recommendations.length >
            0 && (

            <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold">

              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-emerald-400">

                <CheckCircle2
                  size={12}
                />

                {budgetStats.under} under

              </span>

              {budgetStats.near >
                0 && (

                <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-amber-400">

                  <AlertTriangle
                    size={12}
                  />

                  {budgetStats.near} near limit

                </span>

              )}

              {budgetStats.over >
                0 && (

                <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-rose-400">

                  <XCircle
                    size={12}
                  />

                  {budgetStats.over} over

                </span>

              )}

            </div>

          )}

        </div>

        {recommendations.length ===
        0 ? (

          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-5 text-center">

            <p className="text-sm text-slate-500">
              No budget recommendations available yet.
            </p>

          </div>

        ) : (

          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">

            {recommendations
              .slice(0, 6)
              .map(
                (
                  recommendation
                ) => {

                  const averageMonthly =
                    Number(
                      recommendation.average_monthly ||
                        0
                    );

                  const recommendedBudget =
                    Number(
                      recommendation.recommended_budget ||
                        0
                    );

                  const currentMonthSpending =
                    Number(
                      recommendation.current_month_spending ||
                        0
                    );

                  const budgetUsedPct =
                    Number(
                      recommendation.budget_used_pct ||
                        0
                    );

                  const remainingBudget =
                    Number(
                      recommendation.remaining_budget ??
                        (recommendedBudget -
                          currentMonthSpending)
                    );

                  const projectedMonthlySpending =
                    Number(
                      recommendation.projected_monthly_spending ||
                        0
                    );

                  const progress =
                    getBudgetProgress(
                      recommendation
                    );

                  const status =
                    getBudgetStatus(
                      recommendation
                    );

                  return (

                    <div
                      key={
                        recommendation.category
                      }
                      className="rounded-xl bg-slate-900/60 border border-white/5 p-4 transition-all hover:border-white/10 hover:bg-slate-900/80"
                    >

                      <div className="flex items-start justify-between gap-3">

                        <div className="min-w-0">

                          <p className="font-semibold text-white truncate">
                            {
                              recommendation.category
                            }
                          </p>

                          <p className="text-[11px] text-slate-500 mt-1">
                            90-day average{" "}
                            {formatINR(
                              averageMonthly
                            )}
                            /month
                          </p>

                        </div>

                        <span
                          className={`shrink-0 inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[9px] uppercase tracking-wide font-black ${status.className}`}
                        >
                          {status.icon}
                          {status.label}
                        </span>

                      </div>

                      <div className="grid grid-cols-2 gap-2 mt-4">

                        <div className="rounded-lg bg-slate-950/40 border border-white/5 p-2.5">

                          <p className="text-[10px] text-slate-500">
                            Recommended
                          </p>

                          <p className="text-base font-black text-blue-400 mt-0.5">
                            {formatINR(
                              recommendedBudget
                            )}
                          </p>

                        </div>

                        <div className="rounded-lg bg-slate-950/40 border border-white/5 p-2.5">

                          <p className="text-[10px] text-slate-500">
                            This month
                          </p>

                          <p
                            className={`text-base font-black mt-0.5 ${
                              currentMonthSpending >
                              recommendedBudget
                                ? "text-rose-400"
                                : "text-white"
                            }`}
                          >
                            {formatINR(
                              currentMonthSpending
                            )}
                          </p>

                        </div>

                      </div>

                      <div className="mt-3">

                        <div className="flex items-center justify-between mb-1.5">

                          <span className="text-[10px] text-slate-500">
                            Budget used
                          </span>

                          <span
                            className={`text-[10px] font-bold ${
                              budgetUsedPct >
                              100
                                ? "text-rose-400"
                                : budgetUsedPct >=
                                  80
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {budgetUsedPct.toFixed(
                              1
                            )}
                            %
                          </span>

                        </div>

                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">

                          <div
                            className={`h-full rounded-full transition-all ${
                              budgetUsedPct >
                              100
                                ? "bg-rose-500"
                                : budgetUsedPct >=
                                  80
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                            }`}
                            style={{
                              width: `${progress}%`,
                            }}
                          />

                        </div>

                      </div>

                      <div className="grid grid-cols-2 gap-2 mt-3 text-[10px]">

                        <div>

                          <p className="text-slate-500">
                            Remaining
                          </p>

                          <p
                            className={`font-bold mt-0.5 ${
                              remainingBudget <
                              0
                                ? "text-rose-400"
                                : "text-slate-300"
                            }`}
                          >
                            {formatINR(
                              remainingBudget
                            )}
                          </p>

                        </div>

                        <div>

                          <p className="text-slate-500">
                            Projected
                          </p>

                          <p
                            className={`font-bold mt-0.5 ${
                              projectedMonthlySpending >
                              recommendedBudget
                                ? "text-amber-400"
                                : "text-slate-300"
                            }`}
                          >
                            {formatINR(
                              projectedMonthlySpending
                            )}
                          </p>

                        </div>

                      </div>

                      {recommendation.buffer !==
                        undefined && (

                        <p className="text-[10px] text-slate-500 mt-3">
                          Includes{" "}
                          {formatINR(
                            Number(
                              recommendation.buffer ||
                                0
                            )
                          )}{" "}
                          planning buffer.
                        </p>

                      )}

                      {recommendation.reason && (

                        <div className="mt-3 rounded-lg border border-white/5 bg-slate-950/30 px-3 py-2">

                          <p className="text-[10px] leading-4 text-slate-400">
                            {
                              recommendation.reason
                            }
                          </p>

                        </div>

                      )}

                    </div>

                  );
                }
              )}

          </div>

        )}

      </div>

      {/* =====================================================
          MONTHLY REPORT
      ===================================================== */}

      <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <h2 className="font-bold text-white mb-4">
          What changed this month?
        </h2>

        <div className="grid sm:grid-cols-3 gap-4">

          {/* INCOME */}

          <div>

            <p className="text-xs text-slate-500">
              Income
            </p>

            <p className="text-xl font-black text-white">
              {formatINR(
                report?.income ||
                  0
              )}
            </p>

            <p className="text-xs text-emerald-400 flex items-center gap-1 mt-1">

              {report?.income_change_pct >=
              0 ? (
                <TrendingUp
                  size={13}
                />
              ) : (
                <TrendingDown
                  size={13}
                />
              )}

              {Math.abs(
                report?.income_change_pct ||
                  0
              ).toFixed(1)}
              % vs last month

            </p>

          </div>

          {/* EXPENSES */}

          <div>

            <p className="text-xs text-slate-500">
              Expenses
            </p>

            <p className="text-xl font-black text-white">
              {formatINR(
                report?.expenses ||
                  0
              )}
            </p>

            <p className="text-xs text-amber-400 flex items-center gap-1 mt-1">

              {report?.expense_change_pct >=
              0 ? (
                <TrendingUp
                  size={13}
                />
              ) : (
                <TrendingDown
                  size={13}
                />
              )}

              {Math.abs(
                report?.expense_change_pct ||
                  0
              ).toFixed(1)}
              % vs last month

            </p>

          </div>

          {/* SAVINGS */}

          <div>

            <p className="text-xs text-slate-500">
              Savings
            </p>

            <p className="text-xl font-black text-white">
              {formatINR(
                report?.savings ||
                  0
              )}
            </p>

            <p className="text-xs text-blue-400 mt-1">
              {Number(
                report?.savings_rate ||
                  0
              ).toFixed(1)}
              % savings rate
            </p>

          </div>

        </div>

      </div>

      {/* =====================================================
          ANOMALIES
      ===================================================== */}

      <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <div className="flex items-center gap-2 mb-4">

          <AlertTriangle
            size={18}
            className="text-amber-400"
          />

          <h2 className="font-bold text-white">
            Anomaly review (
            {anomalies.length}
            )
          </h2>

        </div>

        {anomalies.length ===
        0 ? (

          <p className="text-sm text-slate-500">
            No unusual spending detected.
          </p>

        ) : (

          <div className="space-y-3">

            {anomalies
              .slice(0, 8)
              .map(
                (anomaly) => (

                  <div
                    key={`${anomaly.transaction_id}-${anomaly.anomaly_type}`}
                    className="rounded-xl bg-amber-500/5 border border-amber-500/10 p-4"
                  >

                    <div className="flex justify-between">

                      <span className="font-semibold text-slate-200">
                        {anomaly.merchant ||
                          "Unknown"}
                      </span>

                      <span className="text-xs font-bold uppercase text-amber-400">
                        {
                          anomaly.severity
                        }
                      </span>

                    </div>

                    <p className="text-sm text-slate-400 mt-1">
                      {
                        anomaly.message
                      }
                    </p>

                  </div>

                )
              )}

          </div>

        )}

        <p className="text-xs text-slate-500 mt-4">
          Anomalies are review flags, not confirmed fraud.
        </p>

      </div>

    </div>
  );
}