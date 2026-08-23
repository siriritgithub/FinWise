import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Edit3, ImagePlus, Mail, Phone, Save, ShieldCheck, Trash2, UserRound, WalletCards, X } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import { useAuthStore } from "../store/authStore";

interface ProfileForm {
  full_name: string; username: string; phone_number: string; date_of_birth: string;
  gender: string; occupation: string; monthly_salary: string; country: string;
  currency: string; timezone: string; language: string; theme: string;
}

const completenessFields: (keyof ProfileForm)[] = ["full_name","username","phone_number","date_of_birth","gender","occupation","monthly_salary","country","currency","timezone","language","theme"];

export default function Settings() {
  const { user, setUser, logout } = useAuthStore();
  const [editing, setEditing] = useState(false);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Record<string,string>>({});
  const [form, setForm] = useState<ProfileForm>({
    full_name:user?.full_name??"", username:user?.username??"", phone_number:user?.phone_number??"", date_of_birth:user?.date_of_birth??"",
    gender:user?.gender??"", occupation:user?.occupation??"", monthly_salary:user?.monthly_salary?.toString()??"", country:user?.country??"India",
    currency:user?.currency??"INR", timezone:user?.timezone??"Asia/Kolkata", language:user?.language??"en", theme:user?.theme??"system"
  });
  const [savedForm,setSavedForm]=useState(form);
  const profilePhoto = user?.profile_photo_path ? `${api.defaults.baseURL?.replace(/\/api\/?$/,'') || 'http://localhost:8000'}/${user.profile_photo_path.replace(/\\/g,'/')}` : null;

  useEffect(()=>{
    const next: ProfileForm={full_name:user?.full_name??"",username:user?.username??"",phone_number:user?.phone_number??"",date_of_birth:user?.date_of_birth??"",gender:user?.gender??"",occupation:user?.occupation??"",monthly_salary:user?.monthly_salary?.toString()??"",country:user?.country??"India",currency:user?.currency??"INR",timezone:user?.timezone??"Asia/Kolkata",language:user?.language??"en",theme:user?.theme??"system"};
    setForm(next); setSavedForm(next);
  },[user]);

  const dirty = JSON.stringify(form)!==JSON.stringify(savedForm) || !!photoFile;
  const completeness = useMemo(()=>Math.round(completenessFields.reduce((n,k)=>n+(String(form[k]??"").trim()?1:0),0)/completenessFields.length*100),[form]);

  const saveMutation=useMutation({
    mutationFn: async()=>{
      const payload={...form, monthly_salary:form.monthly_salary===""?null:Number(form.monthly_salary), date_of_birth:form.date_of_birth||null};
      const response=await api.put("/users/me",payload);
      if(photoFile){ const fd=new FormData(); fd.append("file",photoFile); await api.post("/users/me/profile-photo",fd,{headers:{"Content-Type":"multipart/form-data"}}); }
      return api.get("/users/me");
    },
    onSuccess:({data})=>{ setUser(data); setForm({...form,monthly_salary:data.monthly_salary?.toString()??""}); setSavedForm({...form,monthly_salary:data.monthly_salary?.toString()??""}); setPhotoFile(null); setPhotoPreview(null); setEditing(false); toast.success("Profile saved successfully"); },
    onError:(e:any)=>toast.error(e?.response?.data?.detail||"Unable to save profile")
  });

  const update=(key:keyof ProfileForm,value:string)=>setForm(v=>({...v,[key]:value}));
  const validate=()=>{const e:Record<string,string>={}; if(!form.full_name.trim())e.full_name="Full name is required"; if(form.phone_number && !/^[+0-9 ()-]{7,20}$/.test(form.phone_number))e.phone_number="Enter a valid phone number"; if(form.monthly_salary && Number(form.monthly_salary)<0)e.monthly_salary="Income cannot be negative"; if(form.date_of_birth && form.date_of_birth>new Date().toISOString().slice(0,10))e.date_of_birth="Date of birth cannot be in the future"; setErrors(e); return Object.keys(e).length===0;};
  const save=()=>{if(validate())saveMutation.mutate()};
  const cancel=()=>{setForm(savedForm);setErrors({});setPhotoFile(null);setPhotoPreview(null);setEditing(false)};
  const selectPhoto=(e:React.ChangeEvent<HTMLInputElement>)=>{const f=e.target.files?.[0];if(!f)return;if(f.size>5*1024*1024){toast.error("Profile photo must be under 5 MB");return;}if(!["image/jpeg","image/png","image/webp"].includes(f.type)){toast.error("Use JPG, PNG or WebP");return;}setPhotoFile(f);setPhotoPreview(URL.createObjectURL(f));};
  const removePhoto=async()=>{try{await api.delete("/users/me/profile-photo"); if(user)setUser({...user,profile_photo_path:null}); setPhotoFile(null);setPhotoPreview(null);toast.success("Profile photo removed")}catch{toast.error("Unable to remove photo")}};
  const avatar=photoPreview||profilePhoto;
  const initials=(form.full_name||form.username||"FW").split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("").toUpperCase();

  return <div className="space-y-6 max-w-6xl text-slate-100">
    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4"><div><p className="text-sm font-medium text-blue-300 mb-1">Personalization & security</p><h1 className="text-3xl font-bold text-white">Settings</h1><p className="text-slate-400 mt-1">Manage your identity, preferences and how FinWise personalizes your financial insights.</p></div><div className="flex items-center gap-3 glass-panel px-4 py-3"><Avatar src={avatar} initials={initials}/><div><p className="text-sm font-semibold text-white">{form.full_name||"Your profile"}</p><p className="text-xs text-slate-400">{user?.email}</p></div></div></div>

    <div className="rounded-2xl p-6 bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 shadow-2xl shadow-blue-950/30"><div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5"><div><p className="text-sm text-blue-100">Financial profile</p><h2 className="text-xl font-bold mt-1">{completeness===100?"You're all set":"Complete your profile"}</h2><p className="text-sm text-blue-100 mt-1 max-w-2xl">A complete profile helps FinWise personalize forecasts, savings insights and recommendations.</p></div><div className="min-w-56"><div className="flex justify-between text-xs text-blue-100 mb-2"><span>Profile completeness</span><span>{completeness}%</span></div><div className="h-2 rounded-full bg-white/20 overflow-hidden"><div className="h-full bg-white transition-all duration-500" style={{width:`${completeness}%`}}/></div></div></div></div>

    <div className="grid xl:grid-cols-3 gap-6">
      <section className="xl:col-span-2 dark-card p-6">
        <div className="flex items-start justify-between mb-7"><div className="flex items-start gap-3"><div className="icon-box"><UserRound size={19}/></div><div><h2 className="section-dark-title">Personal profile</h2><p className="muted-dark">Your identity and personal information.</p></div></div>{!editing&&<button onClick={()=>setEditing(true)} className="dark-secondary"><Edit3 size={15}/> Edit profile</button>}</div>
        <div className="grid md:grid-cols-[auto_1fr] gap-7 mb-8"><div className="flex flex-col items-center gap-3"><Avatar src={avatar} initials={initials} large/>{editing&&<div className="flex gap-2"><label className="dark-secondary cursor-pointer"><ImagePlus size={15}/> Upload<input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={selectPhoto}/></label>{(avatar||photoFile)&&<button type="button" onClick={photoFile?()=>{setPhotoFile(null);setPhotoPreview(null)}:removePhoto} className="dark-danger"><Trash2 size={15}/></button>}</div>}</div><div className="grid md:grid-cols-2 gap-4">
          <Field label="Full Name" value={form.full_name} disabled={!editing} onChange={v=>update("full_name",v)} error={errors.full_name} placeholder="Your full name" required/>
          <Field label="Username" value={form.username} disabled error={errors.username} helper="Username is generated from your sign-in identity."/>
          <Field label="Email" value={user?.email||""} disabled helper="Email changes will be added through a secure verification flow." icon={<Mail size={14}/>}/>
          <Field label="Phone Number" value={form.phone_number} disabled={!editing} onChange={v=>update("phone_number",v)} error={errors.phone_number} placeholder="+91 98765 43210" icon={<Phone size={14}/>}/>
          <Field label="Date of Birth" type="date" value={form.date_of_birth} disabled={!editing} onChange={v=>update("date_of_birth",v)} error={errors.date_of_birth}/>
          <SelectField label="Gender" value={form.gender} disabled={!editing} onChange={v=>update("gender",v)} options={[["","Prefer not to say"],["female","Female"],["male","Male"],["non_binary","Non-binary"]]}/>
          <Field label="Occupation / Profession" value={form.occupation} disabled={!editing} onChange={v=>update("occupation",v)} placeholder="e.g. Software Engineer"/>
          <Field label="Expected Monthly Income (INR)" type="number" value={form.monthly_salary} disabled={!editing} onChange={v=>update("monthly_salary",v)} error={errors.monthly_salary} placeholder="50000"/>
          <Field label="Country" value={form.country} disabled={!editing} onChange={v=>update("country",v)} placeholder="India"/>
        </div></div>
        {editing&&<div className="flex items-center justify-between gap-4 pt-5 border-t border-white/10"><p className="text-xs text-slate-500">{dirty?"You have unsaved changes.":"No changes yet."}</p><div className="flex gap-2"><button onClick={cancel} className="dark-secondary"><X size={15}/> Cancel</button><button onClick={save} disabled={!dirty||saveMutation.isPending} className="dark-primary"><Save size={15}/>{saveMutation.isPending?"Saving...":"Save Changes"}</button></div></div>}
      </section>

      <div className="space-y-6">
        <section className="dark-card p-6"><div className="flex items-start gap-3 mb-5"><div className="icon-box green"><WalletCards size={19}/></div><div><h2 className="section-dark-title">Preferences</h2><p className="muted-dark">Control how FinWise displays your finances.</p></div></div><div className="space-y-4"><SelectField label="Display Currency" value={form.currency} disabled={!editing} onChange={v=>update("currency",v)} options={[["INR","INR — Indian Rupee (₹)"],["USD","USD — US Dollar ($)"],["EUR","EUR — Euro (€)"],["GBP","GBP — Pound (£)"]]}/><SelectField label="Timezone" value={form.timezone} disabled={!editing} onChange={v=>update("timezone",v)} options={[["Asia/Kolkata","Asia/Kolkata (IST)"],["UTC","UTC"],["Asia/Dubai","Asia/Dubai"]]}/><SelectField label="Language" value={form.language} disabled={!editing} onChange={v=>update("language",v)} options={[["en","English"],["hi","Hindi"]]}/><SelectField label="Theme" value={form.theme} disabled={!editing} onChange={v=>update("theme",v)} options={[["light","Light ☀"],["dark","Dark ◐"],["system","System ◌"]]}/></div></section>
        <section className="dark-card p-6"><div className="flex items-start gap-3 mb-4"><div className="icon-box amber"><ShieldCheck size={19}/></div><div><h2 className="section-dark-title">Why this matters</h2><p className="muted-dark">How your profile powers FinWise.</p></div></div><div className="space-y-4 text-sm"><Info title="Income" text="Improves savings-rate, affordability and cash-flow calculations."/><Info title="Country & currency" text="Keeps financial displays and recommendations relevant to your region."/><Info title="Occupation" text="Adds context to personalized planning without storing sensitive banking credentials."/><Info title="Preferences" text="Controls how your dashboard, reports and future notifications are presented."/></div></section>
        <section className="dark-card p-6"><h2 className="section-dark-title mb-2">Security</h2><p className="muted-dark">FinWise uses JWT authentication and hashed passwords. Never store bank passwords, UPI PINs or card PINs here.</p></section>
        <button onClick={logout} className="w-full dark-danger justify-center"><ShieldCheck size={15}/> Sign out</button>
      </div>
    </div>
  </div>
}

function Avatar({src,initials,large=false}:{src:string|null,initials:string,large?:boolean}){return src?<img src={src} alt="Profile" className={`${large?"w-28 h-28":"w-11 h-11"} rounded-full object-cover border border-white/10 shadow-xl`}/>:<div className={`${large?"w-28 h-28 text-3xl":"w-11 h-11 text-sm"} rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center font-bold text-white border border-white/10 shadow-xl`}>{initials||"FW"}</div>}
function Field({label,value,onChange,disabled,type="text",placeholder,error,helper,icon,required=false}:{label:string,value:string,onChange?:(v:string)=>void,disabled?:boolean,type?:string,placeholder?:string,error?:string,helper?:string,icon?:React.ReactNode,required?:boolean}){return <div><label className="dark-label">{label}{required&&<span className="text-rose-400"> *</span>}</label><div className="relative">{icon&&<span className="absolute left-3 top-3 text-slate-500">{icon}</span>}<input type={type} value={value} disabled={disabled} onChange={e=>onChange?.(e.target.value)} placeholder={placeholder} className={`dark-input ${icon?"pl-9":""} ${error?"border-rose-500/70":""}`}/></div>{error?<p className="text-xs text-rose-400 mt-1">{error}</p>:helper?<p className="text-xs text-slate-500 mt-1">{helper}</p>:null}</div>}
function SelectField({label,value,onChange,disabled,options}:{label:string,value:string,onChange:(v:string)=>void,disabled?:boolean,options:string[][]}){return <div><label className="dark-label">{label}</label><select value={value} disabled={disabled} onChange={e=>onChange(e.target.value)} className="dark-input"><option value="">Select</option>{options.map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></div>}
function Info({title,text}:{title:string,text:string}){return <div><p className="font-semibold text-slate-200">{title}</p><p className="text-slate-500 mt-1">{text}</p></div>}
