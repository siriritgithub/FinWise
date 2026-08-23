import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { UserRound, Mail, LockKeyhole } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import { useAuthStore } from "../store/authStore";
import type { TokenResponse } from "../types";

interface FormData { email: string; password: string; full_name: string; }

export default function Register() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>();
  const { setUser } = useAuthStore();
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: (data: FormData) => api.post<TokenResponse>("/auth/register", data),
    onSuccess: async ({ data }) => { localStorage.setItem("access_token", data.access_token); localStorage.setItem("refresh_token", data.refresh_token); const me = await api.get("/users/me"); setUser(me.data); toast.success("Welcome to FinWise!"); navigate("/dashboard"); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Registration failed"),
  });
  return <AuthShell eyebrow="Start fresh" title="Build better money habits" subtitle="Create your FinWise account and turn everyday financial data into clear decisions.">
    <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
      <Field icon={<UserRound size={16}/>} label="Full Name" error={errors.full_name?.message}><input {...register("full_name", { required: "Full name is required", minLength: {value:2,message:"Enter at least 2 characters"} })} className="auth-input" placeholder="Your full name"/></Field>
      <Field icon={<Mail size={16}/>} label="Email" error={errors.email?.message}><input {...register("email", { required:"Email is required" })} type="email" className="auth-input" placeholder="you@example.com"/></Field>
      <Field icon={<LockKeyhole size={16}/>} label="Password" error={errors.password?.message}><input {...register("password", { required:"Password is required", minLength:{value:8,message:"Use at least 8 characters"} })} type="password" className="auth-input" placeholder="At least 8 characters"/></Field>
      <button type="submit" disabled={mutation.isPending} className="auth-primary w-full">{mutation.isPending ? "Creating your account..." : "Create my FinWise account"}</button>
    </form>
    <p className="mt-6 text-center text-sm text-slate-500">Already have an account? <Link to="/login" className="font-semibold text-blue-300">Sign in</Link></p>
  </AuthShell>;
}
function Field({label,icon,error,children}:{label:string,icon:React.ReactNode,error?:string,children:React.ReactNode}){return <div><label className="auth-label">{label}</label><div className="auth-input-wrap">{icon}{children}</div>{error&&<p className="auth-error">{error}</p>}</div>}
function AuthShell({eyebrow,title,subtitle,children}:{eyebrow:string,title:string,subtitle:string,children:React.ReactNode}){return <div className="min-h-screen bg-[#060b16] text-white"><div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(37,99,235,.20),transparent_30%),radial-gradient(circle_at_85%_70%,rgba(6,182,212,.10),transparent_28%)]"/><div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-10 lg:grid-cols-2"><div className="hidden lg:block"><Link to="/" className="text-2xl font-black">Fin<span className="text-cyan-300">Wise</span></Link><p className="mt-12 text-sm font-semibold uppercase tracking-[.2em] text-blue-300">{eyebrow}</p><h1 className="mt-4 max-w-xl text-5xl font-black leading-tight">{title}</h1><p className="mt-5 max-w-lg text-lg leading-8 text-slate-400">{subtitle}</p></div><div className="mx-auto w-full max-w-md rounded-[2rem] border border-white/10 bg-[#0d1628]/95 p-7 shadow-2xl shadow-black/40 sm:p-8"><div className="mb-7 lg:hidden"><Link to="/" className="text-2xl font-black">Fin<span className="text-cyan-300">Wise</span></Link></div><div className="mb-7"><p className="text-xs font-semibold uppercase tracking-[.18em] text-blue-300">{eyebrow}</p><h2 className="mt-2 text-2xl font-bold">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-400">{subtitle}</p></div>{children}</div></div></div>}
