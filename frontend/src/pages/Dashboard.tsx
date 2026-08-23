import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowDownRight, ArrowUpRight, Loader2, Wallet,
  Plus, ReceiptText, Target, Sparkles, TrendingUp,
} from "lucide-react";
import api from "../lib/api";
import type { DashboardSummary } from "../types";
import { formatINR } from "../lib/utils";
import { DashboardAlerts } from "../components/DashboardAlerts";
import { CashflowChart } from "../components/CashflowChart";
import { DashboardBudgets } from "../components/DashboardBudgets";
import { RecentTransactions } from "../components/RecentTransactions";
import type { ElementType } from "react";

interface StatCardProps {
  title: string;
  value: string;
  icon: ElementType;
  change?: number;
  tone: "blue" | "green" | "violet" | "amber";
}

const toneMap = {
  blue: "bg-blue-500/10 text-blue-400 ring-blue-400/15",
  green: "bg-emerald-500/10 text-emerald-400 ring-emerald-400/15",
  violet: "bg-violet-500/10 text-violet-400 ring-violet-400/15",
  amber: "bg-amber-500/10 text-amber-400 ring-amber-400/15",
};

const StatCard = ({ title, value, icon: Icon, change, tone }: StatCardProps) => (
  <div className="group bg-[#111a2b] rounded-2xl border border-white/10 p-5 shadow-xl shadow-black/10 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-black/20 transition-all">
    <div className="flex items-start justify-between">
      <div className={`h-11 w-11 rounded-xl ring-1 flex items-center justify-center ${toneMap[tone]}`}>
        <Icon size={21} />
      </div>
      {typeof change === "number" && (
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${change >= 0 ? "bg-emerald-500/10 text-emerald-300" : "bg-rose-500/10 text-rose-300"}`}>
          {change >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
          {Math.abs(change).toFixed(1)}%
        </span>
      )}
    </div>
    <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</p>
    <p className="mt-1 text-2xl font-black tracking-tight text-white">{value}</p>
    {typeof change === "number" && <p className="mt-1 text-[11px] text-slate-400">vs. previous month</p>}
  </div>
);

const fetchDashboardSummary = async (): Promise<DashboardSummary> => {
  const { data } = await api.get("/analytics/dashboard-summary");
  return data;
};

const Dashboard = () => {
  const { data, isLoading, error } = useQuery<DashboardSummary>({
    queryKey: ["dashboardSummary"],
    queryFn: fetchDashboardSummary,
  });

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-[60vh]"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;
  }

  if (error) {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">Failed to load dashboard data. Please refresh and try again.</div>;
  }

  return (
    <div className="page-shell">
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-900 px-6 py-7 lg:px-8 lg:py-8 text-white shadow-xl shadow-blue-950/10">
        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-cyan-400/15 blur-3xl" />
        <div className="absolute right-1/4 -bottom-28 h-64 w-64 rounded-full bg-blue-400/10 blur-3xl" />
        <div className="relative flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[11px] font-semibold text-blue-100">
              <Sparkles size={13} /> Your financial command center
            </div>
            <h1 className="mt-4 text-3xl lg:text-4xl font-black tracking-tight">Know your money. Grow your future.</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100/75">Track spending, understand your cash flow and make smarter decisions with data-driven insights.</p>
          </div>
          <div className="flex gap-2">
            <Link to="/transactions" className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-500 transition-colors"><Plus size={16} /> Add transaction</Link>
            <Link to="/chat" className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-2.5 text-sm font-bold text-white hover:bg-white/15 transition-colors"><Sparkles size={16} /> Ask FinWise</Link>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mt-5">
        <StatCard title="Total balance" value={formatINR(data?.total_balance ?? 0)} icon={Wallet} tone="blue" />
        <StatCard title="Income this month" value={formatINR(data?.this_month_income.total ?? 0)} icon={ArrowUpRight} change={data?.this_month_income.change} tone="green" />
        <StatCard title="Expenses this month" value={formatINR(data?.this_month_expenses.total ?? 0)} icon={ArrowDownRight} change={data?.this_month_expenses.change} tone="violet" />
        <StatCard title="Savings rate" value={`${(data?.savings_rate ?? 0).toFixed(1)}%`} icon={TrendingUp} tone="amber" />
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
        <Link to="/accounts" className="group rounded-2xl border border-white/10 bg-[#111a2b] p-4 hover:border-blue-400/30 hover:shadow-md transition-all"><div className="flex items-center gap-3"><Wallet size={18} className="text-blue-600" /><div><p className="text-sm font-bold text-slate-100">Manage accounts</p><p className="text-xs text-slate-400">Keep balances accurate</p></div><ArrowUpRight size={15} className="ml-auto text-slate-300 group-hover:text-blue-600" /></div></Link>
        <Link to="/receipts" className="group rounded-2xl border border-white/10 bg-[#111a2b] p-4 hover:border-blue-400/30 hover:shadow-md transition-all"><div className="flex items-center gap-3"><ReceiptText size={18} className="text-violet-600" /><div><p className="text-sm font-bold text-slate-100">Scan a receipt</p><p className="text-xs text-slate-400">Turn receipts into data</p></div><ArrowUpRight size={15} className="ml-auto text-slate-300 group-hover:text-blue-600" /></div></Link>
        <Link to="/goals" className="group rounded-2xl border border-white/10 bg-[#111a2b] p-4 hover:border-blue-400/30 hover:shadow-md transition-all"><div className="flex items-center gap-3"><Target size={18} className="text-emerald-600" /><div><p className="text-sm font-bold text-slate-100">Review your goals</p><p className="text-xs text-slate-400">Stay on your plan</p></div><ArrowUpRight size={15} className="ml-auto text-slate-300 group-hover:text-blue-600" /></div></Link>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mt-5">
        <div className="xl:col-span-2 space-y-5"><CashflowChart /><DashboardBudgets /></div>
        <div className="space-y-5"><RecentTransactions /><DashboardAlerts /></div>
      </div>
    </div>
  );
};

export default Dashboard;
