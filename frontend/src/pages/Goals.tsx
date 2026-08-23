import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Dialog } from "@headlessui/react";
import { Plus, Pencil, Trash2, Target, ChevronRight } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import ConfirmDialog from "../components/ConfirmDialog";
import { formatINR } from "../lib/utils";
import type { SavingsGoal, GoalPlan } from "../types";

export default function Goals() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SavingsGoal | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [planGoalId, setPlanGoalId] = useState<number | null>(null);
  const { register, handleSubmit, reset, setValue } = useForm<any>();

  const { data: goals = [] } = useQuery<SavingsGoal[]>({
    queryKey: ["goals"],
    queryFn: () => api.get("/goals").then((r) => r.data),
  });

  const { data: plan } = useQuery<GoalPlan>({
    queryKey: ["goal-plan", planGoalId],
    queryFn: () => api.get(`/goals/${planGoalId}/plan`).then((r) => r.data),
    enabled: planGoalId !== null,
  });

  const saveMutation = useMutation({
    mutationFn: (data: any) =>
      editing ? api.put(`/goals/${editing.id}`, data) : api.post("/goals", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      toast.success(editing ? "Goal updated" : "Goal created");
      setShowForm(false); setEditing(null); reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/goals/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["goals"] }); setDeleteId(null); },
  });

  const openEdit = (g: SavingsGoal) => {
    setEditing(g);
    setValue("name", g.name); setValue("target_amount", g.target_amount);
    setValue("current_amount", g.current_amount); setValue("deadline", g.deadline);
    setValue("priority", g.priority); setValue("monthly_contribution", g.monthly_contribution);
    setShowForm(true);
  };

  const priorityColor: Record<string, string> = {
    high: "bg-red-100 text-red-700",
    medium: "bg-yellow-100 text-yellow-700",
    low: "bg-green-100 text-green-700",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Savings Goals</h1>
        <button onClick={() => { setEditing(null); reset(); setShowForm(true); }} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Add Goal
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {goals.map((g) => {
          const pct = Math.min((Number(g.current_amount) / Number(g.target_amount)) * 100, 100);
          return (
            <div key={g.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Target size={18} className="text-blue-500" />
                  <p className="font-semibold text-gray-800">{g.name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColor[g.priority]}`}>
                    {g.priority}
                  </span>
                  <button onClick={() => openEdit(g)} className="text-gray-400 hover:text-blue-600"><Pencil size={14} /></button>
                  <button onClick={() => setDeleteId(g.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={14} /></button>
                </div>
              </div>

              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500">{formatINR(Number(g.current_amount))} saved</span>
                <span className="font-semibold text-gray-800">{formatINR(Number(g.target_amount))}</span>
              </div>
              <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden mb-3">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
              </div>
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{pct.toFixed(1)}% complete</span>
                {g.deadline && <span>Deadline: {g.deadline}</span>}
              </div>
              <button
                onClick={() => setPlanGoalId(g.id)}
                className="mt-3 text-xs text-blue-600 hover:underline flex items-center gap-1"
              >
                View plan <ChevronRight size={12} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Plan Dialog */}
      <Dialog open={planGoalId !== null} onClose={() => setPlanGoalId(null)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <Dialog.Title className="font-semibold text-gray-900 mb-4">Goal Plan</Dialog.Title>
            {plan ? (
              <div className="space-y-3 text-sm">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 text-xs">Months Remaining</p>
                    <p className="font-bold text-gray-800 text-lg">{plan.months_remaining ?? "—"}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 text-xs">Required Monthly</p>
                    <p className="font-bold text-gray-800 text-lg">{plan.required_monthly ? formatINR(plan.required_monthly) : "—"}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 text-xs">Current Surplus</p>
                    <p className={`font-bold text-lg ${Number(plan.current_surplus) >= 0 ? "text-green-600" : "text-red-600"}`}>
                      {formatINR(Number(plan.current_surplus))}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 text-xs">Achievable?</p>
                    <p className={`font-bold text-lg ${plan.is_achievable ? "text-green-600" : "text-red-600"}`}>
                      {plan.is_achievable ? "Yes" : "Needs adjustment"}
                    </p>
                  </div>
                </div>
                {plan.tradeoff_suggestions.length > 0 && (
                  <div className="bg-blue-50 rounded-lg p-3">
                    <p className="font-medium text-blue-800 mb-2">Suggestions</p>
                    {plan.tradeoff_suggestions.map((s, i) => (
                      <p key={i} className="text-blue-700 text-xs mb-1">• {s}</p>
                    ))}
                  </div>
                )}
              </div>
            ) : <p className="text-gray-400 text-sm">Loading plan...</p>}
            <button onClick={() => setPlanGoalId(null)} className="btn-secondary text-sm mt-4 w-full">Close</button>
          </Dialog.Panel>
        </div>
      </Dialog>

      {/* Add/Edit Dialog */}
      <Dialog open={showForm} onClose={() => setShowForm(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <Dialog.Title className="font-semibold text-gray-900 mb-4">
              {editing ? "Edit Goal" : "New Goal"}
            </Dialog.Title>
            <form onSubmit={handleSubmit((d) => saveMutation.mutate(d))} className="space-y-3">
              <div>
                <label className="label">Goal Name</label>
                <input {...register("name", { required: true })} className="input" placeholder="e.g. Emergency Fund" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Target Amount</label>
                  <input {...register("target_amount", { required: true, valueAsNumber: true })} type="number" className="input" />
                </div>
                <div>
                  <label className="label">Current Amount</label>
                  <input {...register("current_amount", { valueAsNumber: true })} type="number" className="input" defaultValue={0} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Deadline</label>
                  <input {...register("deadline")} type="date" className="input" />
                </div>
                <div>
                  <label className="label">Priority</label>
                  <select {...register("priority")} className="input">
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Monthly Contribution (INR)</label>
                <input {...register("monthly_contribution", { valueAsNumber: true })} type="number" className="input" />
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
        open={deleteId !== null} title="Delete Goal"
        message="Remove this savings goal?"
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
        onCancel={() => setDeleteId(null)} loading={deleteMutation.isPending}
      />
    </div>
  );
}
