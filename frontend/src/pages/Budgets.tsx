import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Dialog } from "@headlessui/react";
import { Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import BudgetProgress from "../components/BudgetProgress";
import ConfirmDialog from "../components/ConfirmDialog";
import { currentMonth } from "../lib/utils";
import type { Budget, BudgetSummary, Category } from "../types";

export default function Budgets() {
  const qc = useQueryClient();
  const [month, setMonth] = useState(currentMonth());
  const [showForm, setShowForm] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const { register, handleSubmit, reset } = useForm<any>();

  const { data: summary = [] } = useQuery<BudgetSummary[]>({
    queryKey: ["budget-summary", month],
    queryFn: () => api.get(`/budgets/summary?month=${month}`).then((r) => r.data),
  });

  const { data: budgets = [] } = useQuery<Budget[]>({
    queryKey: ["budgets", month],
    queryFn: () => api.get(`/budgets?month=${month}`).then((r) => r.data),
  });

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => api.get("/categories").then((r) => r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (data: any) => api.post("/budgets", { ...data, month }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["budget-summary"] });
      toast.success("Budget saved");
      setShowForm(false); reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/budgets/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["budget-summary"] });
      setDeleteId(null);
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Budgets</h1>
        <div className="flex gap-3">
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="input w-40"
          />
          <button onClick={() => { reset(); setShowForm(true); }} className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={16} /> Add Budget
          </button>
        </div>
      </div>

      {summary.length > 0 ? (
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-5">Spending vs Budget — {month}</h2>
          <BudgetProgress items={summary} />
        </div>
      ) : (
        <div className="card text-center py-12 text-gray-400">
          No budgets set for {month}. Add one to start tracking.
        </div>
      )}

      {/* Budget list with delete */}
      {budgets.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-4">Budget Limits</h2>
          <div className="space-y-2">
            {budgets.map((b) => {
              const cat = categories.find((c) => c.id === b.category_id);
              return (
                <div key={b.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <span className="text-sm text-gray-700">{cat?.name || "Total"}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-gray-800">₹{Number(b.amount).toLocaleString("en-IN")}</span>
                    <button onClick={() => setDeleteId(b.id)} className="text-gray-400 hover:text-red-600">
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <Dialog open={showForm} onClose={() => setShowForm(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
            <Dialog.Title className="font-semibold text-gray-900 mb-4">Add Budget</Dialog.Title>
            <form onSubmit={handleSubmit((d) => saveMutation.mutate(d))} className="space-y-3">
              <div>
                <label className="label">Category</label>
                <select {...register("category_id", { valueAsNumber: true })} className="input">
                  <option value="">Total (all categories)</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Budget Amount (INR)</label>
                <input {...register("amount", { required: true, valueAsNumber: true })} type="number" className="input" />
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
        open={deleteId !== null} title="Delete Budget"
        message="Remove this budget limit?"
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
        onCancel={() => setDeleteId(null)} loading={deleteMutation.isPending}
      />
    </div>
  );
}
