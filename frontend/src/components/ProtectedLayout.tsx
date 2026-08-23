import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { Bell, ChevronRight, Plus, Search } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import Sidebar from "./Sidebar";

const labels: Record<string, string> = {
  dashboard: "Dashboard",
  transactions: "Transactions",
  accounts: "Accounts",
  categories: "Categories",
  budgets: "Budgets",
  subscriptions: "Subscriptions",
  goals: "Goals",
  receipts: "Receipts",
  analytics: "Analytics",
  chat: "AI Assistant",
  settings: "Settings",
};

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();
  const hasToken = !!localStorage.getItem("access_token");

  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const page = labels[location.pathname.split("/")[1]] || "Dashboard";
  const firstName = user?.full_name?.split(" ")[0] || "there";
  // FinWise uses a consistent dark workspace theme across the application.
  const isLight = false;

  return (
    <div className={`dark-workspace flex min-h-screen ${isLight ? "bg-slate-100" : "bg-[#080d19]"}`}>
      <Sidebar />
      <div className={`flex-1 min-w-0 flex flex-col ${isLight ? "bg-slate-100" : "bg-[#0b1220]"}`}>
        <header className={`h-[76px] ${isLight ? "bg-white/90 border-slate-200" : "bg-[#0d1526]/90 border-white/10"} backdrop-blur-xl border-b sticky top-0 z-20 px-6 lg:px-8 flex items-center justify-between`}>
          <div className="flex items-center gap-2 text-sm">
            <span className={isLight ? "text-slate-400" : "text-slate-500"}>FinWise</span>
            <ChevronRight size={15} className="text-slate-300" />
            <span className={isLight ? "font-semibold text-slate-800" : "font-semibold text-slate-200"}>{page}</span>
          </div>

          <div className="flex items-center gap-2">
            <div className={`hidden md:flex items-center gap-2 rounded-xl px-3 py-2 w-52 ${isLight ? "bg-slate-50 border border-slate-200" : "bg-white/5 border border-white/10"}`}>
              <Search size={16} className="text-slate-400" />
              <span className="text-xs text-slate-500">Search your finances</span>
              <span className="ml-auto text-[10px] text-slate-400 border border-slate-200 rounded px-1.5 py-0.5">⌘K</span>
            </div>
            <button className={`h-10 w-10 rounded-xl ${isLight ? "border border-slate-200 bg-white text-slate-500" : "border border-white/10 bg-white/5 text-slate-400"} hover:bg-slate-500/10 transition-colors`} title="Notifications">
              <Bell size={17} className="mx-auto" />
            </button>
            <button onClick={() => navigate("/transactions")} className="btn-primary hidden sm:inline-flex">
              <Plus size={16} /> Add transaction
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="px-5 py-6 lg:px-8 lg:py-8">
            <div className="mb-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-400">Personal finance command center</p>
              <h2 className={`mt-1 text-xl font-bold tracking-tight ${isLight ? "text-slate-900" : "text-white"}`}>Good to see you, {firstName}.</h2>
            </div>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
