import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, LockKeyhole, Mail, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import { useAuthStore } from "../store/authStore";
import type { TokenResponse } from "../types";

interface FormData { email: string; password: string; }

export default function Login() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>();
  const { login } = useAuthStore();
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: (data: FormData) => api.post<TokenResponse>("/auth/login", data),
    onSuccess: async ({ data }) => { await login(data); navigate("/dashboard"); },
    onError: () => toast.error("Invalid email or password"),
  });

  return <AuthShell eyebrow="Welcome back" title="Continue your financial journey" subtitle="Sign in to see your money, insights and plans in one place.">
    <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
      <div><label className="auth-label">Email</label><div className="auth-input-wrap"><Mail size={16}/><input {...register("email", { required: "Email is required" })} type="email" className="auth-input" placeholder="you@example.com" /></div>{errors.email&&<p className="auth-error">{errors.email.message}</p>}</div>
      <div><label className="auth-label">Password</label><div className="auth-input-wrap"><LockKeyhole size={16}/><input {...register("password", { required: "Password is required" })} type="password" className="auth-input" placeholder="••••••••" /></div>{errors.password&&<p className="auth-error">{errors.password.message}</p>}</div>
      <div className="flex justify-end"><Link to="/forgot-password" className="text-xs font-semibold text-cyan-300 hover:text-cyan-200">Forgot password?</Link></div>
      <button type="submit" disabled={mutation.isPending} className="auth-primary w-full">{mutation.isPending ? "Signing in..." : "Sign in to FinWise"}</button>
    </form>
    <p className="mt-6 text-center text-sm text-slate-500">New to FinWise? <Link to="/register" className="font-semibold text-blue-300 hover:text-blue-200">Create an account</Link></p>
    <Link to="/" className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-500 hover:text-slate-300"><ArrowLeft size={14}/> Back to FinWise</Link>
  </AuthShell>;
}

function AuthShell({eyebrow,title,subtitle,children}:{eyebrow:string,title:string,subtitle:string,children:React.ReactNode}) {
  return <div className="min-h-screen bg-[#060b16] text-white"><div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(37,99,235,.20),transparent_30%),radial-gradient(circle_at_85%_70%,rgba(6,182,212,.10),transparent_28%)]"/><div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-10 lg:grid-cols-2">
    <div className="hidden lg:block"><Link to="/" className="inline-flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-400 to-cyan-300 text-slate-950"><Sparkles size={20}/></div><span className="text-2xl font-black">Fin<span className="text-cyan-300">Wise</span></span></Link><p className="mt-12 text-sm font-semibold uppercase tracking-[.2em] text-blue-300">{eyebrow}</p><h1 className="mt-4 max-w-xl text-5xl font-black leading-tight">{title}</h1><p className="mt-5 max-w-lg text-lg leading-8 text-slate-400">{subtitle}</p><div className="mt-8 grid max-w-lg gap-3 sm:grid-cols-2"><Benefit text="Track spending and cash flow"/><Benefit text="Plan budgets and savings goals"/><Benefit text="Ask FinWise in natural language"/><Benefit text="Get data-driven insights"/></div></div>
    <div className="mx-auto w-full max-w-md rounded-[2rem] border border-white/10 bg-[#0d1628]/95 p-7 shadow-2xl shadow-black/40 backdrop-blur-xl sm:p-8"><div className="mb-7 lg:hidden"><Link to="/" className="text-2xl font-black">Fin<span className="text-cyan-300">Wise</span></Link></div><div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[.18em] text-blue-300">{eyebrow}</p><h2 className="mt-2 text-2xl font-bold">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-400">{subtitle}</p></div>{children}</div>
  </div></div>;
}
function Benefit({text}:{text:string}){return <div className="rounded-xl border border-white/10 bg-white/[.035] px-4 py-3 text-sm text-slate-300">✓ {text}</div>}
