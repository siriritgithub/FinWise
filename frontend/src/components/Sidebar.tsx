import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ArrowLeftRight, Wallet, Tag, PieChart,
  RefreshCw, Target, Receipt, BarChart2, MessageSquare,
  Settings, LogOut, Sparkles, CircleDollarSign,
} from "lucide-react";
import { useAuthStore } from "../store/authStore";

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/transactions", icon: ArrowLeftRight, label: "Transactions" },
  { to: "/accounts", icon: Wallet, label: "Accounts" },
  { to: "/categories", icon: Tag, label: "Categories" },
  { to: "/budgets", icon: PieChart, label: "Budgets" },
  { to: "/subscriptions", icon: RefreshCw, label: "Subscriptions" },
  { to: "/goals", icon: Target, label: "Goals" },
  { to: "/receipts", icon: Receipt, label: "Receipts" },
  { to: "/analytics", icon: BarChart2, label: "Analytics" },
];

const TOOLS = [
  { to: "/chat", icon: MessageSquare, label: "AI Assistant" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  const { logout, user } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="w-[272px] bg-[#0b1220] text-white flex flex-col h-screen sticky top-0 shrink-0 shadow-2xl shadow-slate-900/10">
      <div className="px-5 pt-6 pb-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-blue-400 to-cyan-300 flex items-center justify-center shadow-lg shadow-blue-900/30">
            <CircleDollarSign size={23} className="text-slate-950" />
          </div>
          <div>
            <div className="text-xl font-black tracking-tight">
              Fin<span className="text-cyan-300">Wise</span>
            </div>
            <p className="text-[11px] text-slate-400">Financial intelligence platform</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5">
        <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">Workspace</p>
        <div className="space-y-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-[#172338] text-white border border-white/10 shadow-lg shadow-black/20"
                    : "text-slate-300 hover:bg-white/8 hover:text-white"
                }`
              }
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 group-[.active]:bg-blue-500/15">
                <Icon size={17} />
              </span>
              {label}
            </NavLink>
          ))}
        </div>

        <p className="px-3 mt-7 mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">Intelligence</p>
        <div className="space-y-1">
          {TOOLS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-blue-500 to-cyan-400 text-white shadow-lg shadow-blue-900/30"
                    : "text-slate-300 hover:bg-white/8 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
              {label === "AI Assistant" && <Sparkles size={14} className="ml-auto text-cyan-300" />}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="p-3 border-t border-white/10">
        <div className="rounded-2xl bg-white/5 border border-white/10 p-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-sm font-bold">
              {(user?.full_name || user?.email || "U").charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold truncate">{user?.full_name || "FinWise User"}</p>
              <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-3 w-full flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-slate-400 hover:text-white hover:bg-red-500/15 transition-colors"
          >
            <LogOut size={15} /> Logout
          </button>
        </div>
      </div>
    </aside>
  );
}
