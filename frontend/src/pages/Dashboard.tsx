import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  ArrowDownRight,
  ArrowUpRight,
  Loader2,
  Wallet,
  Plus,
  ReceiptText,
  Target,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  CalendarDays,
  Activity,
  PiggyBank,
} from "lucide-react";

import api from "../lib/api";
import type { DashboardSummary } from "../types";
import { formatINR } from "../lib/utils";

import { DashboardAlerts } from "../components/DashboardAlerts";
import { CashflowChart } from "../components/CashflowChart";
import { DashboardBudgets } from "../components/DashboardBudgets";
import { RecentTransactions } from "../components/RecentTransactions";

import type { ElementType } from "react";

/* =========================================================
   TYPES
========================================================= */

interface StatCardProps {
  title: string;
  value: string;
  icon: ElementType;
  change?: number;
  tone: "blue" | "green" | "violet" | "amber";
}

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
};

/* =========================================================
   SMART SAVINGS PLAN
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
   STAT CARD
========================================================= */

const toneMap = {
  blue:
    "bg-blue-500/10 text-blue-400 ring-blue-400/15",

  green:
    "bg-emerald-500/10 text-emerald-400 ring-emerald-400/15",

  violet:
    "bg-violet-500/10 text-violet-400 ring-violet-400/15",

  amber:
    "bg-amber-500/10 text-amber-400 ring-amber-400/15",
};

const StatCard = ({
  title,
  value,
  icon: Icon,
  change,
  tone,
}: StatCardProps) => (
  <div className="group bg-[#111a2b] rounded-2xl border border-white/10 p-5 shadow-xl shadow-black/10 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-black/20 transition-all">

    <div className="flex items-start justify-between">

      <div
        className={`h-11 w-11 rounded-xl ring-1 flex items-center justify-center ${toneMap[tone]}`}
      >
        <Icon size={21} />
      </div>

      {typeof change === "number" && (
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${
            change >= 0
              ? "bg-emerald-500/10 text-emerald-300"
              : "bg-rose-500/10 text-rose-300"
          }`}
        >
          {change >= 0 ? (
            <ArrowUpRight size={13} />
          ) : (
            <ArrowDownRight size={13} />
          )}

          {Math.abs(change).toFixed(1)}%
        </span>
      )}

    </div>

    <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-slate-400">
      {title}
    </p>

    <p className="mt-1 text-2xl font-black tracking-tight text-white">
      {value}
    </p>

    {typeof change === "number" && (
      <p className="mt-1 text-[11px] text-slate-400">
        vs. previous month
      </p>
    )}

  </div>
);

/* =========================================================
   DASHBOARD API
========================================================= */

const fetchDashboardSummary =
  async (): Promise<DashboardSummary> => {
    const { data } =
      await api.get(
        "/analytics/dashboard-summary"
      );

    return data;
  };

/* =========================================================
   DASHBOARD
========================================================= */

const Dashboard = () => {

  /* -------------------------------------------------------
     DASHBOARD SUMMARY
  ------------------------------------------------------- */

  const {
    data,
    isLoading,
    isFetching,
    error,
  } = useQuery<DashboardSummary>({
    queryKey: ["dashboardSummary"],

    queryFn:
      fetchDashboardSummary,

    staleTime: 0,

    refetchOnMount: "always",

    refetchOnWindowFocus: true,
  });

  /* -------------------------------------------------------
     CASHFLOW FORECAST
  ------------------------------------------------------- */

  const {
    data: forecast,
    isLoading: forecastLoading,
  } = useQuery<ForecastResponse>({
    queryKey: ["dashboard-cashflow"],

    queryFn: () =>
      api
        .get(
          "/analytics/cashflow?days=30"
        )
        .then((r) => r.data),

    staleTime: 0,

    refetchOnMount: "always",
  });

  /* -------------------------------------------------------
     FINANCIAL INSIGHTS
  ------------------------------------------------------- */

  const {
    data: insightsData,
    isLoading: insightsLoading,
  } = useQuery<InsightsResponse>({
    queryKey: [
      "dashboard-financial-insights",
    ],

    queryFn: () =>
      api
        .get("/analytics/insights")
        .then((r) => r.data),

    staleTime: 0,

    refetchOnMount: "always",
  });

  /* -------------------------------------------------------
     SMART SAVINGS PLAN
  ------------------------------------------------------- */

  const {
    data: savingsPlan,
    isLoading: savingsPlanLoading,
  } = useQuery<SavingsPlanResponse>({
    queryKey: [
      "dashboard-savings-plan",
    ],

    queryFn: () =>
      api
        .get(
          "/analytics/savings-plan"
        )
        .then((r) => r.data),

    staleTime: 0,

    refetchOnMount: "always",
  });

  /* -------------------------------------------------------
     LOADING
  ------------------------------------------------------- */

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
      </div>
    );
  }

  /* -------------------------------------------------------
     ERROR
  ------------------------------------------------------- */

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-5 text-sm text-rose-300">
        Failed to load dashboard data.
        Please refresh and try again.
      </div>
    );
  }

  /* -------------------------------------------------------
     FORECAST VALUES
  ------------------------------------------------------- */

  const currentBalance = Number(
    forecast?.current_balance ??
      data?.total_balance ??
      0
  );

  const projectedEndingBalance =
    Number(
      forecast?.projected_ending_balance ??
        currentBalance
    );

  const expectedIncome = Number(
    forecast?.expected_income ?? 0
  );

  const expectedExpenses = Number(
    forecast?.expected_expenses ?? 0
  );

  const netCashFlow = Number(
    forecast?.net_cash_flow ??
      expectedIncome -
        expectedExpenses
  );

  const lowestProjectedBalance =
    Number(
      forecast?.lowest_projected_balance ??
        currentBalance
    );

  const overallStatus =
    forecast?.overall_status ||
    "safe";

  /* -------------------------------------------------------
     TOP INSIGHT
  ------------------------------------------------------- */

  const topInsight =
    insightsData?.insights?.[0];

  const topAction =
    insightsData?.recommended_actions?.[0];

  /* -------------------------------------------------------
     LOW BALANCE
  ------------------------------------------------------- */

  const hasLowBalance =
    forecast?.forecast?.some(
      (item) =>
        item.is_low_balance
    ) || false;

  /* -------------------------------------------------------
     STATUS UI
  ------------------------------------------------------- */

  const statusConfig =
    overallStatus === "safe"
      ? {
          label: "Safe",
          icon: CheckCircle2,
          classes:
            "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
        }
      : overallStatus === "caution"
      ? {
          label: "Caution",
          icon: AlertTriangle,
          classes:
            "bg-amber-500/10 border-amber-500/20 text-amber-300",
        }
      : {
          label: "At risk",
          icon: AlertTriangle,
          classes:
            "bg-rose-500/10 border-rose-500/20 text-rose-300",
        };

  const StatusIcon =
    statusConfig.icon;

  /* -------------------------------------------------------
     SMART SAVINGS VALUES
  ------------------------------------------------------- */

  const recommendedSavings =
    Number(
      savingsPlan?.recommended_savings ??
        0
    );

  const safeToSpend =
    Number(
      savingsPlan?.safe_to_spend ??
        0
    );

  const goalContribution =
    Number(
      savingsPlan?.required_goal_contribution ??
        0
    );

  const goalPressure =
    Number(
      savingsPlan?.goal_pressure ??
        0
    );

  const savingsPlanStatus =
    savingsPlan?.financial_status ||
    "unknown";

  const savingsStatusConfig: Record<
    string,
    {
      label: string;
      classes: string;
    }
  > = {
    healthy: {
      label: "Healthy",
      classes:
        "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
    },

    on_track: {
      label: "On track",
      classes:
        "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
    },

    goal_pressure: {
      label: "Goal pressure",
      classes:
        "bg-amber-500/10 border-amber-500/20 text-amber-300",
    },

    caution: {
      label: "Caution",
      classes:
        "bg-amber-500/10 border-amber-500/20 text-amber-300",
    },

    critical: {
      label: "Critical",
      classes:
        "bg-rose-500/10 border-rose-500/20 text-rose-300",
    },

    unknown: {
      label: "Unavailable",
      classes:
        "bg-slate-500/10 border-slate-500/20 text-slate-400",
    },
  };

  const savingsStatus =
    savingsStatusConfig[
      savingsPlanStatus
    ] ||
    savingsStatusConfig.unknown;

  const savingsCapacityPct =
    Number(
      savingsPlan?.monthly_income ??
        0
    ) > 0
      ? Math.min(
          Math.max(
            (recommendedSavings /
              Number(
                savingsPlan?.monthly_income ??
                  1
              )) *
              100,
            0
          ),
          100
        )
      : 0;

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <div className="page-shell space-y-5">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-900 px-6 py-7 lg:px-8 lg:py-8 text-white shadow-xl shadow-blue-950/10">

        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-cyan-400/15 blur-3xl" />

        <div className="absolute right-1/4 -bottom-28 h-64 w-64 rounded-full bg-blue-400/10 blur-3xl" />

        <div className="relative flex flex-col lg:flex-row lg:items-end justify-between gap-6">

          <div>

            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[11px] font-semibold text-blue-100">

              <Sparkles size={13} />

              Your financial command center

            </div>

            <h1 className="mt-4 text-3xl lg:text-4xl font-black tracking-tight">
              Know your money. Grow your future.
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100/75">
              Track spending, understand your cash flow
              and make smarter decisions with
              data-driven insights.
            </p>

          </div>

          <div className="flex gap-2">

            <Link
              to="/transactions"
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-500 transition-colors"
            >
              <Plus size={16} />
              Add transaction
            </Link>

            <Link
              to="/chat"
              className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-2.5 text-sm font-bold text-white hover:bg-white/15 transition-colors"
            >
              <Sparkles size={16} />
              Ask FinWise
            </Link>

          </div>

        </div>

      </section>

      {/* =====================================================
          DASHBOARD STATS
      ===================================================== */}

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

        <StatCard
          title="Total balance"
          value={formatINR(
            data?.total_balance ?? 0
          )}
          icon={Wallet}
          tone="blue"
        />

        <StatCard
          title="Income this month"
          value={formatINR(
            data?.this_month_income?.total ?? 0
          )}
          icon={ArrowUpRight}
          change={
            data?.this_month_income?.change
          }
          tone="green"
        />

        <StatCard
          title="Expenses this month"
          value={formatINR(
            data?.this_month_expenses?.total ?? 0
          )}
          icon={ArrowDownRight}
          change={
            data?.this_month_expenses?.change
          }
          tone="violet"
        />

        <StatCard
          title="Savings rate"
          value={`${(
            data?.savings_rate ?? 0
          ).toFixed(1)}%`}
          icon={TrendingUp}
          tone="amber"
        />

      </section>

      {/* =====================================================
          SMART SAVINGS SNAPSHOT
      ===================================================== */}

      <section className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-400/15 flex items-center justify-center">
              <PiggyBank size={21} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Smart Savings Plan
              </h2>

              <p className="text-xs text-slate-400 mt-0.5">
                Your personalized savings, spending and goal snapshot.
              </p>

            </div>

          </div>

          {savingsPlan && (
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold ${savingsStatus.classes}`}
            >
              {savingsPlanStatus ===
                "healthy" ||
              savingsPlanStatus ===
                "on_track" ? (
                <CheckCircle2 size={14} />
              ) : (
                <AlertTriangle size={14} />
              )}

              {savingsStatus.label}
            </span>
          )}

        </div>

        {savingsPlanLoading ? (

          <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mt-5">

            {[1, 2, 3, 4].map(
              (item) => (
                <div
                  key={item}
                  className="rounded-xl border border-white/5 bg-slate-900/60 p-4 animate-pulse"
                >
                  <div className="h-3 w-24 bg-slate-800 rounded" />

                  <div className="h-6 w-32 bg-slate-800 rounded mt-3" />

                  <div className="h-2 w-20 bg-slate-800 rounded mt-2" />
                </div>
              )
            )}

          </div>

        ) : savingsPlan ? (

          <>

            {/* =================================================
                SAVINGS METRICS
            ================================================= */}

            <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mt-5">

              <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

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
                    recommendedSavings
                  )}
                </p>

                <p className="text-[10px] text-slate-500 mt-1">
                  {Number(
                    savingsPlan.savings_rate ??
                      0
                  ).toFixed(1)}
                  % savings rate
                </p>

              </div>

              <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

                <div className="flex items-center justify-between">

                  <p className="text-[11px] text-slate-500">
                    Safe to spend
                  </p>

                  <Wallet
                    size={15}
                    className="text-blue-400"
                  />

                </div>

                <p className="text-xl font-black text-blue-400 mt-2">
                  {formatINR(
                    safeToSpend
                  )}
                </p>

                <p className="text-[10px] text-slate-500 mt-1">
                  Flexible monthly spending
                </p>

              </div>

              <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

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
                    goalContribution
                  )}
                </p>

                <p className="text-[10px] text-slate-500 mt-1">
                  Monthly-equivalent pace
                </p>

              </div>

              <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

                <div className="flex items-center justify-between">

                  <p className="text-[11px] text-slate-500">
                    Monthly surplus
                  </p>

                  <TrendingUp
                    size={15}
                    className="text-emerald-400"
                  />

                </div>

                <p className="text-xl font-black text-white mt-2">
                  {formatINR(
                    Number(
                      savingsPlan.monthly_surplus ??
                        0
                    )
                  )}
                </p>

                <p className="text-[10px] text-slate-500 mt-1">
                  Income minus expenses
                </p>

              </div>

            </div>

            {/* =================================================
                SAVINGS CAPACITY
            ================================================= */}

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
                  {savingsCapacityPct.toFixed(1)}%
                </span>

              </div>

              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">

                <div
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{
                    width: `${savingsCapacityPct}%`,
                  }}
                />

              </div>

              <div className="flex justify-between mt-2 text-[10px]">

                <span className="text-slate-500">
                  Income{" "}
                  {formatINR(
                    Number(
                      savingsPlan.monthly_income ??
                        0
                    )
                  )}
                </span>

                <span className="text-slate-400">
                  Save{" "}
                  {formatINR(
                    recommendedSavings
                  )}
                </span>

              </div>

            </div>

            {/* =================================================
                GOAL PRESSURE
            ================================================= */}

            {goalPressure > 0 && (

              <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">

                <div className="flex items-start gap-3">

                  <AlertTriangle
                    size={17}
                    className="text-amber-400 mt-0.5 shrink-0"
                  />

                  <div>

                    <p className="text-xs font-bold text-amber-300">
                      Goal pressure detected
                    </p>

                    <p className="text-[11px] leading-5 text-slate-400 mt-1">

                      Your active goal commitments are approximately{" "}

                      <span className="font-bold text-amber-300">
                        {formatINR(
                          goalPressure
                        )}
                      </span>{" "}

                      above the safer savings amount.
                      Consider reducing discretionary spending
                      or adjusting a goal deadline.

                    </p>

                  </div>

                </div>

              </div>

            )}

            {/* =================================================
                GOALS
            ================================================= */}

            {savingsPlan.goals?.length >
              0 && (

              <div className="mt-5">

                <div className="flex items-center justify-between mb-3">

                  <div>

                    <p className="text-sm font-bold text-white">
                      Goal priorities
                    </p>

                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Goals currently affecting your savings plan
                    </p>

                  </div>

                  <Link
                    to="/goals"
                    className="text-[11px] font-bold text-blue-400 hover:text-blue-300"
                  >
                    View goals
                  </Link>

                </div>

                <div className="space-y-2">

                  {savingsPlan.goals
                    .slice(0, 3)
                    .map((goal) => {

                      const current =
                        Number(
                          goal.current_amount ??
                            0
                        );

                      const remaining =
                        Number(
                          goal.remaining_amount ??
                            0
                        );

                      /*
                       * Use current + remaining for the displayed
                       * target so the dashboard remains consistent
                       * with the corrected Analytics goal calculation.
                       */
                      const target =
                        remaining >= 0
                          ? current +
                            remaining
                          : Number(
                              goal.target_amount ??
                                0
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

                      return (

                        <div
                          key={goal.id}
                          className="rounded-xl border border-white/5 bg-slate-900/50 p-3"
                        >

                          <div className="flex items-center justify-between gap-3">

                            <div className="min-w-0">

                              <div className="flex items-center gap-2">

                                <p className="text-xs font-semibold text-slate-200 truncate">
                                  {goal.name}
                                </p>

                                {goal.priority && (

                                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[8px] uppercase font-bold text-slate-500">
                                    {goal.priority}
                                  </span>

                                )}

                              </div>

                              {goal.deadline && (

                                <p className="text-[10px] text-slate-500 mt-1">

                                  <CalendarDays
                                    size={11}
                                    className="inline mr-1"
                                  />

                                  Deadline{" "}

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

                                  {goal.days_remaining !==
                                    undefined &&
                                    ` · ${
                                      goal.days_remaining
                                    } day${
                                      goal.days_remaining ===
                                      1
                                        ? ""
                                        : "s"
                                    } left`}

                                </p>

                              )}

                            </div>

                            <div className="text-right shrink-0">

                              <p className="text-xs font-black text-white">

                                {formatINR(
                                  current
                                )}

                                {" / "}

                                {formatINR(
                                  target
                                )}

                              </p>

                              <p className="text-[9px] text-slate-500">
                                {progress.toFixed(
                                  0
                                )}
                                % funded
                              </p>

                            </div>

                          </div>

                          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mt-2.5">

                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{
                                width: `${progress}%`,
                              }}
                            />

                          </div>

                        </div>

                      );

                    })}

                </div>

              </div>

            )}

            {/* =================================================
                SAVINGS RECOMMENDATION
            ================================================= */}

            {savingsPlan.recommendations
              ?.length > 0 && (

              <div className="mt-5 border-t border-white/10 pt-4">

                <div className="flex items-center gap-2 mb-3">

                  <Lightbulb
                    size={16}
                    className="text-blue-400"
                  />

                  <p className="text-sm font-bold text-white">
                    Savings recommendation
                  </p>

                </div>

                <div className="rounded-xl border border-blue-500/10 bg-blue-500/5 p-3">

                  <p className="text-xs leading-5 text-slate-300">
                    {
                      savingsPlan
                        .recommendations[0]
                    }
                  </p>

                </div>

              </div>

            )}

          </>

        ) : (

          <div className="mt-5 rounded-xl border border-white/5 bg-slate-900/40 p-4">

            <p className="text-sm text-slate-500">
              Smart savings data is not available yet.
            </p>

          </div>

        )}

      </section>

      {/* =====================================================
          CASHFLOW INTELLIGENCE
      ===================================================== */}

      <section className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">

          <div className="flex items-center gap-3">

            <div className="h-11 w-11 rounded-xl bg-blue-500/10 text-blue-400 ring-1 ring-blue-400/15 flex items-center justify-center">
              <Activity size={21} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Cash-flow outlook
              </h2>

              <p className="text-xs text-slate-400 mt-0.5">
                Your projected financial position over the next 30 days
              </p>

            </div>

          </div>

          <div
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold ${statusConfig.classes}`}
          >

            <StatusIcon size={14} />

            {statusConfig.label}

          </div>

        </div>

        {/* FORECAST METRICS */}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">

          <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

            <p className="text-[11px] text-slate-500">
              Current balance
            </p>

            <p className="text-lg font-black text-white mt-1">
              {formatINR(
                currentBalance
              )}
            </p>

          </div>

          <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

            <p className="text-[11px] text-slate-500">
              Expected income
            </p>

            <p className="text-lg font-black text-emerald-400 mt-1">
              {formatINR(
                expectedIncome
              )}
            </p>

          </div>

          <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

            <p className="text-[11px] text-slate-500">
              Expected expenses
            </p>

            <p className="text-lg font-black text-rose-400 mt-1">
              {formatINR(
                expectedExpenses
              )}
            </p>

          </div>

          <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">

            <p className="text-[11px] text-slate-500">
              Projected ending
            </p>

            <p
              className={`text-lg font-black mt-1 ${
                projectedEndingBalance >=
                currentBalance
                  ? "text-emerald-400"
                  : "text-amber-400"
              }`}
            >
              {formatINR(
                projectedEndingBalance
              )}
            </p>

          </div>

        </div>

        {/* NET CASHFLOW */}

        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">

          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-3">

            <div className="flex items-center justify-between">

              <span className="text-xs text-slate-500">
                Net cash flow
              </span>

              <span
                className={`text-sm font-black ${
                  netCashFlow >= 0
                    ? "text-emerald-400"
                    : "text-rose-400"
                }`}
              >

                {netCashFlow >= 0
                  ? "+"
                  : ""}

                {formatINR(
                  netCashFlow
                )}

              </span>

            </div>

          </div>

          <div className="rounded-xl border border-white/5 bg-slate-900/40 p-3">

            <div className="flex items-center justify-between">

              <span className="text-xs text-slate-500">
                Lowest projected balance
              </span>

              <span
                className={`text-sm font-black ${
                  lowestProjectedBalance <
                  3000
                    ? "text-rose-400"
                    : lowestProjectedBalance <
                      6000
                    ? "text-amber-400"
                    : "text-emerald-400"
                }`}
              >
                {formatINR(
                  lowestProjectedBalance
                )}
              </span>

            </div>

            {forecast?.lowest_balance_date && (

              <p className="text-[10px] text-slate-600 mt-1">

                Expected on{" "}

                {new Date(
                  forecast.lowest_balance_date
                ).toLocaleDateString(
                  "en-GB"
                )}

              </p>

            )}

          </div>

        </div>

        {/* LOW BALANCE WARNING */}

        {hasLowBalance && (

          <div className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">

            <div className="flex items-center gap-2 text-rose-300">

              <AlertTriangle size={16} />

              <p className="text-xs font-bold">
                Cash-flow warning
              </p>

            </div>

            <p className="text-[11px] text-slate-400 mt-1">
              Your projected balance falls below
              the ₹3,000 safety threshold during
              the forecast period.
            </p>

          </div>

        )}

        {forecastLoading && (

          <div className="flex items-center justify-center py-8 text-slate-500">

            <Loader2
              size={18}
              className="animate-spin mr-2"
            />

            Updating cash-flow forecast...

          </div>

        )}

      </section>

      {/* =====================================================
          FINANCIAL INSIGHT
      ===================================================== */}

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* TOP INSIGHT */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3 mb-4">

            <div className="h-10 w-10 rounded-xl bg-violet-500/10 text-violet-400 ring-1 ring-violet-400/15 flex items-center justify-center">
              <Sparkles size={19} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Financial insight
              </h2>

              <p className="text-xs text-slate-500">
                Based on your recent financial activity
              </p>

            </div>

          </div>

          {insightsLoading ? (

            <div className="animate-pulse space-y-3">

              <div className="h-4 w-48 bg-slate-800 rounded" />

              <div className="h-3 w-full bg-slate-800 rounded" />

              <div className="h-3 w-4/5 bg-slate-800 rounded" />

            </div>

          ) : topInsight ? (

            <div className="rounded-xl border border-white/5 bg-slate-900/50 p-4">

              <div className="flex items-start gap-3">

                {topInsight.type ===
                "positive" ? (

                  <CheckCircle2
                    size={18}
                    className="text-emerald-400 mt-0.5 shrink-0"
                  />

                ) : topInsight.type ===
                  "warning" ? (

                  <AlertTriangle
                    size={18}
                    className="text-amber-400 mt-0.5 shrink-0"
                  />

                ) : (

                  <Activity
                    size={18}
                    className="text-blue-400 mt-0.5 shrink-0"
                  />

                )}

                <div>

                  <p className="font-semibold text-slate-100">
                    {topInsight.title}
                  </p>

                  <p className="text-xs leading-5 text-slate-400 mt-1">
                    {topInsight.message}
                  </p>

                </div>

              </div>

            </div>

          ) : (

            <p className="text-sm text-slate-500">
              No financial insights available yet.
            </p>

          )}

          <Link
            to="/analytics"
            className="inline-flex items-center gap-1 text-xs font-bold text-blue-400 hover:text-blue-300 mt-4"
          >
            View all analytics
            <ArrowUpRight size={13} />
          </Link>

        </div>

        {/* RECOMMENDED ACTION */}

        <div className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3 mb-4">

            <div className="h-10 w-10 rounded-xl bg-amber-500/10 text-amber-400 ring-1 ring-amber-400/15 flex items-center justify-center">
              <Lightbulb size={19} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Recommended action
              </h2>

              <p className="text-xs text-slate-500">
                One practical step for you
              </p>

            </div>

          </div>

          {insightsLoading ? (

            <div className="animate-pulse space-y-3">

              <div className="h-3 w-full bg-slate-800 rounded" />

              <div className="h-3 w-5/6 bg-slate-800 rounded" />

            </div>

          ) : topAction ? (

            <div className="rounded-xl border border-white/5 bg-slate-900/50 p-4">

              <div className="flex items-start gap-3">

                <span className="h-7 w-7 shrink-0 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center text-xs font-black">
                  1
                </span>

                <p className="text-sm leading-6 text-slate-300">
                  {topAction}
                </p>

              </div>

            </div>

          ) : (

            <p className="text-sm text-slate-500">
              No recommendations available yet.
            </p>

          )}

        </div>

      </section>

      {/* =====================================================
          UPCOMING EVENTS
      ===================================================== */}

      {forecast?.upcoming_events &&
        forecast.upcoming_events.length >
          0 && (

        <section className="rounded-2xl border border-white/10 bg-[#111a2b] p-5 shadow-xl shadow-black/10">

          <div className="flex items-center gap-3 mb-4">

            <div className="h-10 w-10 rounded-xl bg-blue-500/10 text-blue-400 ring-1 ring-blue-400/15 flex items-center justify-center">
              <CalendarDays size={19} />
            </div>

            <div>

              <h2 className="font-bold text-white">
                Upcoming financial events
              </h2>

              <p className="text-xs text-slate-500">
                Scheduled income and expenses
              </p>

            </div>

          </div>

          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">

            {forecast.upcoming_events
              .slice(0, 6)
              .map(
                (
                  event: any,
                  index: number
                ) => (

                  <div
                    key={index}
                    className="rounded-xl border border-white/5 bg-slate-900/50 p-4"
                  >

                    <div className="flex justify-between gap-3">

                      <div>

                        <p className="text-sm font-semibold text-slate-200">

                          {event.label ||
                            event.description ||
                            event.name ||
                            "Scheduled event"}

                        </p>

                        {event.date && (

                          <p className="text-[10px] text-slate-500 mt-1">

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
                          className={`text-xs font-black ${
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

                  </div>

                )
              )}

          </div>

        </section>

      )}

      {/* =====================================================
          QUICK ACTIONS
      ===================================================== */}

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">

        <Link
          to="/accounts"
          className="group rounded-2xl border border-white/10 bg-[#111a2b] p-4 hover:border-blue-400/30 hover:shadow-md transition-all"
        >

          <div className="flex items-center gap-3">

            <Wallet
              size={18}
              className="text-blue-400"
            />

            <div>

              <p className="text-sm font-bold text-slate-100">
                Manage accounts
              </p>

              <p className="text-xs text-slate-400">
                Keep balances accurate
              </p>

            </div>

            <ArrowUpRight
              size={15}
              className="ml-auto text-slate-500 group-hover:text-blue-400"
            />

          </div>

        </Link>

        <Link
          to="/receipts"
          className="group rounded-2xl border border-white/10 bg-[#111a2b] p-4 hover:border-blue-400/30 hover:shadow-md transition-all"
        >

          <div className="flex items-center gap-3">

            <ReceiptText
              size={18}
              className="text-violet-400"
            />

            <div>

              <p className="text-sm font-bold text-slate-100">
                Scan a receipt
              </p>

              <p className="text-xs text-slate-400">
                Turn receipts into data
              </p>

            </div>

            <ArrowUpRight
              size={15}
              className="ml-auto text-slate-500 group-hover:text-blue-400"
            />

          </div>

        </Link>

        <Link
          to="/goals"
          className="group rounded-2xl border border-white/10 bg-[#111a2b] p-4 hover:border-blue-400/30 hover:shadow-md transition-all"
        >

          <div className="flex items-center gap-3">

            <Target
              size={18}
              className="text-emerald-400"
            />

            <div>

              <p className="text-sm font-bold text-slate-100">
                Review your goals
              </p>

              <p className="text-xs text-slate-400">
                Stay on your plan
              </p>

            </div>

            <ArrowUpRight
              size={15}
              className="ml-auto text-slate-500 group-hover:text-blue-400"
            />

          </div>

        </Link>

      </section>

      {/* =====================================================
          EXISTING DASHBOARD CONTENT
      ===================================================== */}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        <div className="xl:col-span-2 space-y-5">

          <CashflowChart />

          <DashboardBudgets />

        </div>

        <div className="space-y-5">

          <RecentTransactions />

          <DashboardAlerts />

        </div>

      </div>

      {/* =====================================================
          REFRESH INDICATOR
      ===================================================== */}

      {isFetching &&
        !isLoading && (

        <div className="fixed bottom-5 right-5 flex items-center gap-2 rounded-full bg-[#111a2b] border border-white/10 px-4 py-2 text-xs text-slate-300 shadow-xl">

          <Loader2
            size={14}
            className="animate-spin"
          />

          Updating dashboard...

        </div>

      )}

    </div>
  );
};

export default Dashboard;