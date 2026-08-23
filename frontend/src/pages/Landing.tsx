import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, Bot, ShieldCheck, Sparkles, Target, WalletCards } from "lucide-react";

const features = [
  { icon: BarChart3, title: "See the full picture", text: "Track balances, spending, budgets, goals and cash flow in one place." },
  { icon: Bot, title: "Ask FinWise", text: "Use natural language to understand your money and get personalized insights." },
  { icon: Target, title: "Plan with confidence", text: "Forecast cash flow, model what-if scenarios and work toward savings goals." },
];

export default function Landing() {
  return (
    <div className="min-h-screen overflow-hidden bg-[#060b16] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(37,99,235,.22),transparent_32%),radial-gradient(circle_at_80%_20%,rgba(6,182,212,.14),transparent_28%),linear-gradient(180deg,#0b1220_0%,#060b16_100%)]" />
      <div className="relative mx-auto max-w-7xl px-6 py-6 lg:px-10">
        <header className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-400 to-cyan-300 text-slate-950 shadow-lg shadow-blue-950/40">
              <WalletCards size={21} />
            </div>
            <div>
              <div className="text-xl font-black tracking-tight">Fin<span className="text-cyan-300">Wise</span></div>
              <div className="text-[10px] uppercase tracking-[.18em] text-slate-500">Financial intelligence</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/login" className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-200 hover:bg-white/10 transition">Sign in</Link>
            <Link to="/register" className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-950/30 hover:bg-blue-500 transition">Get started</Link>
          </div>
        </header>

        <main className="grid min-h-[calc(100vh-120px)] items-center gap-14 py-16 lg:grid-cols-[1.1fr_.9fr] lg:py-20">
          <section>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-400/10 px-3 py-1.5 text-xs font-semibold text-blue-200">
              <Sparkles size={14} /> Your personal finance command center
            </div>
            <h1 className="max-w-4xl text-5xl font-black leading-[1.03] tracking-tight sm:text-6xl lg:text-7xl">
              Know your money.
              <span className="block bg-gradient-to-r from-blue-300 via-cyan-200 to-violet-300 bg-clip-text text-transparent">Grow your future.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
              FinWise brings your accounts, transactions, budgets, goals and financial intelligence together — so you can understand what happened, what is coming next, and what to do about it.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register" className="inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-6 py-3.5 font-bold shadow-xl shadow-blue-950/40 hover:bg-blue-500 transition">
                Start using FinWise <ArrowRight size={18} />
              </Link>
              <Link to="/login" className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-6 py-3.5 font-bold text-slate-200 hover:bg-white/10 transition">
                I already have an account
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-5 text-xs text-slate-500">
              <span className="inline-flex items-center gap-2"><ShieldCheck size={15} className="text-emerald-400" /> Secure authentication</span>
              <span className="inline-flex items-center gap-2"><Bot size={15} className="text-cyan-400" /> AI-powered insights</span>
              <span className="inline-flex items-center gap-2"><Target size={15} className="text-violet-400" /> Goal-focused planning</span>
            </div>
          </section>

          <section className="relative">
            <div className="absolute -inset-8 rounded-[3rem] bg-blue-500/10 blur-3xl" />
            <div className="relative rounded-[2rem] border border-white/10 bg-[#0d1628]/90 p-5 shadow-2xl shadow-black/40 backdrop-blur-xl">
              <div className="rounded-2xl border border-white/10 bg-[#111c31] p-5">
                <div className="flex items-center justify-between">
                  <div><p className="text-xs text-slate-500">Financial overview</p><p className="mt-1 text-2xl font-black">₹1,24,580</p></div>
                  <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-300">+12.4%</span>
                </div>
                <div className="mt-7 h-32 rounded-xl bg-gradient-to-t from-blue-500/20 to-transparent p-3">
                  <div className="flex h-full items-end gap-2">
                    {[35,48,42,65,58,78,72,92,84,100].map((h, i) => <div key={i} className="flex-1 rounded-t-md bg-gradient-to-t from-blue-600 to-cyan-300" style={{ height: `${h}%` }} />)}
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4">
                {[
                  ["Savings rate", "24.8%", "text-emerald-300"],
                  ["Health score", "82 / 100", "text-cyan-300"],
                  ["30-day forecast", "₹1,42,900", "text-violet-300"],
                  ["Active goals", "3", "text-blue-300"],
                ].map(([label, value, cls]) => <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.035] p-4"><p className="text-xs text-slate-500">{label}</p><p className={`mt-2 text-lg font-black ${cls}`}>{value}</p></div>)}
              </div>
            </div>
          </section>
        </main>

        <section className="grid gap-4 pb-10 md:grid-cols-3">
          {features.map(({ icon: Icon, title, text }) => <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><Icon className="text-blue-300" size={21}/><h3 className="mt-4 font-bold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{text}</p></div>)}
        </section>
      </div>
    </div>
  );
}
