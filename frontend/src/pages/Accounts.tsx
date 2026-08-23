// Accounts.tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Dialog } from "@headlessui/react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import ConfirmDialog from "../components/ConfirmDialog";
import { formatINR, formatDate } from "../lib/utils";
import type { Account } from "../types";

export function Accounts() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const { register, handleSubmit, reset, setValue } = useForm<any>();

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: () => api.get("/accounts").then((r) => r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (data: any) =>
      editing ? api.put(`/accounts/${editing.id}`, data) : api.post("/accounts", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      toast.success(editing ? "Account updated" : "Account created");
      setShowForm(false); setEditing(null); reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/accounts/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["accounts"] }); setDeleteId(null); },
  });

  const openEdit = (a: Account) => {
    setEditing(a);
    setValue("name", a.name); setValue("type", a.type);
    setValue("balance", a.balance); setValue("credit_limit", a.credit_limit);
    setShowForm(true);
  };

  const ACCOUNT_TYPES = ["bank", "cash", "credit_card", "wallet", "investment", "loan"];
  const typeColors: Record<string, string> = {
    bank: "bg-blue-100 text-blue-700", cash: "bg-green-100 text-green-700",
    credit_card: "bg-purple-100 text-purple-700", wallet: "bg-yellow-100 text-yellow-700",
    investment: "bg-indigo-100 text-indigo-700", loan: "bg-red-100 text-red-700",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
        <button onClick={() => { setEditing(null); reset(); setShowForm(true); }} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Add Account
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map((a) => (
          <div key={a.id} className="card">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-semibold text-gray-800">{a.name}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[a.type] || "bg-gray-100 text-gray-600"}`}>
                  {a.type.replace("_", " ")}
                </span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => openEdit(a)} className="text-gray-400 hover:text-blue-600"><Pencil size={15} /></button>
                <button onClick={() => setDeleteId(a.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={15} /></button>
              </div>
            </div>
            <p className={`text-2xl font-bold ${Number(a.balance) < 0 ? "text-red-600" : "text-gray-900"}`}>
              {formatINR(Number(a.balance))}
            </p>
            {a.credit_limit && (
              <p className="text-xs text-gray-400 mt-1">Limit: {formatINR(Number(a.credit_limit))}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">Since {formatDate(a.created_at)}</p>
          </div>
        ))}
      </div>

      <Dialog open={showForm} onClose={() => setShowForm(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <Dialog.Title className="font-semibold text-gray-900 mb-4">
              {editing ? "Edit Account" : "Add Account"}
            </Dialog.Title>
            <form onSubmit={handleSubmit((d) => saveMutation.mutate(d))} className="space-y-3">
              <div>
                <label className="label">Account Name</label>
                <input {...register("name", { required: true })} className="input" placeholder="e.g. HDFC Savings" />
              </div>
              <div>
                <label className="label">Type</label>
                <select {...register("type", { required: true })} className="input">
                  {ACCOUNT_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Current Balance (INR)</label>
                <input {...register("balance", { valueAsNumber: true })} type="number" step="0.01" className="input" />
              </div>
              <div>
                <label className="label">Credit Limit (for credit cards)</label>
                <input {...register("credit_limit", { valueAsNumber: true })} type="number" step="0.01" className="input" />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
                <button type="submit" disabled={saveMutation.isPending} className="btn-primary text-sm">Save</button>
              </div>
            </form>
          </Dialog.Panel>
        </div>
      </Dialog>

      <ConfirmDialog
        open={deleteId !== null} title="Delete Account"
        message="All transactions in this account will also be deleted."
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
        onCancel={() => setDeleteId(null)} loading={deleteMutation.isPending}
      />
    </div>
  );
}
