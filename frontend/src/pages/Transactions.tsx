import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Dialog } from "@headlessui/react";
import { Plus, Search, Upload, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import ConfirmDialog from "../components/ConfirmDialog";
import { formatINR, formatDate, typeColor } from "../lib/utils";
import type { Transaction, Account, Category } from "../types";

export default function Transactions() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const params = new URLSearchParams({ page: String(page), page_size: "20" });
  if (search) params.set("search", search);
  if (typeFilter) params.set("type", typeFilter);

  const { data: transactions = [], isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions", page, search, typeFilter],
    queryFn: () => api.get(`/transactions?${params}`).then((r) => r.data),
  });

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: () => api.get("/accounts").then((r) => r.data),
  });

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => api.get("/categories").then((r) => r.data),
  });

  const { register, handleSubmit, reset, setValue } = useForm<any>();

  const saveMutation = useMutation({
    mutationFn: (data: any) =>
      editing
        ? api.put(`/transactions/${editing.id}`, data)
        : api.post("/transactions", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      toast.success(editing ? "Transaction updated" : "Transaction added");
      setShowForm(false);
      setEditing(null);
      reset();
    },
    onError: () => toast.error("Failed to save transaction"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/transactions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      toast.success("Deleted");
      setDeleteId(null);
    },
  });

  const openEdit = (t: Transaction) => {
    setEditing(t);
    setValue("account_id", t.account_id);
    setValue("amount", t.amount);
    setValue("type", t.type);
    setValue("merchant", t.merchant);
    setValue("description", t.description);
    setValue("transaction_date", t.transaction_date.slice(0, 16));
    setValue("payment_method", t.payment_method);
    setValue("category_id", t.category_id);
    setShowForm(true);
  };

  const handleCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || accounts.length === 0) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post(
        `/transactions/import-csv?account_id=${accounts[0].id}`,
        fd,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      qc.invalidateQueries({ queryKey: ["transactions"] });
      toast.success(`Imported ${data.imported} transactions`);
    } catch {
      toast.error("CSV import failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
        <div className="flex gap-2">
          <label className="btn-secondary text-sm cursor-pointer flex items-center gap-2">
            <Upload size={16} /> Import CSV
            <input type="file" accept=".csv" className="hidden" onChange={handleCSV} />
          </label>
          <button onClick={() => { setEditing(null); reset(); setShowForm(true); }} className="btn-primary flex items-center gap-2 text-sm">
            <Plus size={16} /> Add
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
          <input
            className="input pl-9 w-64"
            placeholder="Search merchant or description..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <select
          className="input w-40"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
        >
          <option value="">All types</option>
          <option value="income">Income</option>
          <option value="expense">Expense</option>
          <option value="transfer">Transfer</option>
        </select>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              {["Date", "Merchant", "Category", "Amount", "Method", ""].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading ? (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">Loading...</td></tr>
            ) : transactions.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">No transactions found</td></tr>
            ) : transactions.map((t) => {
              const cat = categories.find((c) => c.id === t.category_id);
              return (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500">{formatDate(t.transaction_date)}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{t.merchant || "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{cat?.name || "—"}</td>
                  <td className={`px-4 py-3 font-semibold ${typeColor(t.type)}`}>
                    {t.type === "income" ? "+" : "-"}{formatINR(Number(t.amount))}
                  </td>
                  <td className="px-4 py-3 text-gray-400 capitalize">{t.payment_method}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(t)} className="text-gray-400 hover:text-blue-600">
                        <Pencil size={15} />
                      </button>
                      <button onClick={() => setDeleteId(t.id)} className="text-gray-400 hover:text-red-600">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="flex justify-between items-center px-4 py-3 border-t border-gray-100">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)} className="btn-secondary text-xs disabled:opacity-40">
            Previous
          </button>
          <span className="text-xs text-gray-500">Page {page}</span>
          <button disabled={transactions.length < 20} onClick={() => setPage((p) => p + 1)} className="btn-secondary text-xs disabled:opacity-40">
            Next
          </button>
        </div>
      </div>

      {/* Add/Edit Dialog */}
      <Dialog open={showForm} onClose={() => setShowForm(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg">
            <Dialog.Title className="font-semibold text-gray-900 mb-4">
              {editing ? "Edit Transaction" : "Add Transaction"}
            </Dialog.Title>
            <form onSubmit={handleSubmit((d) => saveMutation.mutate(d))} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Account</label>
                  <select {...register("account_id", { required: true, valueAsNumber: true })} className="input">
                    {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Type</label>
                  <select {...register("type", { required: true })} className="input">
                    <option value="expense">Expense</option>
                    <option value="income">Income</option>
                    <option value="transfer">Transfer</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Amount (INR)</label>
                  <input {...register("amount", { required: true, valueAsNumber: true })} type="number" step="0.01" className="input" />
                </div>
                <div>
                  <label className="label">Date & Time</label>
                  <input {...register("transaction_date", { required: true })} type="datetime-local" className="input" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Merchant</label>
                  <input {...register("merchant")} className="input" placeholder="e.g. Swiggy" />
                </div>
                <div>
                  <label className="label">Payment Method</label>
                  <select {...register("payment_method")} className="input">
                    {["upi", "card", "cash", "netbanking", "other"].map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Category</label>
                <select {...register("category_id", { valueAsNumber: true })} className="input">
                  <option value="">Auto-detect</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Description</label>
                <input {...register("description")} className="input" />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
                <button type="submit" disabled={saveMutation.isPending} className="btn-primary text-sm">
                  {saveMutation.isPending ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </Dialog.Panel>
        </div>
      </Dialog>

      <ConfirmDialog
        open={deleteId !== null}
        title="Delete Transaction"
        message="This action cannot be undone."
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
        onCancel={() => setDeleteId(null)}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
