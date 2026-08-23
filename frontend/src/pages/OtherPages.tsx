// Subscriptions.tsx
import { useForm } from "react-hook-form";
import { useState } from "react";
import { Dialog } from "@headlessui/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Upload, FileText, ChevronDown, ChevronUp, Plus } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import { formatINR } from "../lib/utils";
import type { Subscription, Receipt, Category } from "../types";
import { useAuthStore } from "../store/authStore";

export function Subscriptions() {
  const qc = useQueryClient();

  const { data: subs = [] } = useQuery<Subscription[]>({
    queryKey: ["subscriptions"],
    queryFn: () => api.get("/recurring/subscriptions").then((r) => r.data),
  });

  const detectMutation = useMutation({
    mutationFn: () => api.post("/recurring/detect"),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["subscriptions"] });
      toast.success(`Detected ${r.data.rules_created_or_updated} recurring rules`);
    },
  });

  const totalMonthly = subs.reduce((s, sub) => s + sub.monthly_cost, 0);
  const totalAnnual = subs.reduce((s, sub) => s + sub.annual_cost, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Subscriptions</h1>
        <button
          onClick={() => detectMutation.mutate()}
          disabled={detectMutation.isPending}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw size={16} className={detectMutation.isPending ? "animate-spin" : ""} />
          Detect Recurring
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="card text-center">
          <p className="text-sm text-gray-500">Monthly Cost</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatINR(totalMonthly)}</p>
        </div>
        <div className="card text-center">
          <p className="text-sm text-gray-500">Annual Cost</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatINR(totalAnnual)}</p>
        </div>
      </div>

      {subs.length === 0 ? (
        <div className="card text-center py-12 text-gray-400">
          No subscriptions detected yet. Click "Detect Recurring" to scan your transactions.
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {["Service", "Amount", "Interval", "Next Due", "Monthly Cost"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {subs.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800 capitalize">{s.merchant}</td>
                  <td className="px-4 py-3 text-gray-600">{formatINR(s.expected_amount)}</td>
                  <td className="px-4 py-3 text-gray-500">{s.interval_days}d</td>
                  <td className="px-4 py-3 text-gray-500">{s.next_expected_date || "—"}</td>
                  <td className="px-4 py-3 font-semibold text-gray-800">{formatINR(s.monthly_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Receipts ──────────────────────────────────────────────────────────────────

const ACCEPTED = ".jpg,.jpeg,.png,.pdf,.webp,.bmp,.tiff,.tif";
const MAX_MB = 10;

export function Receipts() {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [lastResult, setLastResult] = useState<any>(null);

  const { data: receipts = [] } = useQuery<Receipt[]>({
    queryKey: ["receipts"],
    queryFn: () => api.get("/receipts").then((r) => r.data),
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset input so same file can be re-uploaded after fix
    e.target.value = "";
    if (!file) return;

    // Client-side size check
    if (file.size > MAX_MB * 1024 * 1024) {
      toast.error(`File too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }

    // Client-side type check
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    const allowed = ["jpg", "jpeg", "png", "pdf", "webp", "bmp", "tiff", "tif"];
    if (!allowed.includes(ext)) {
      toast.error(
        `Invalid file type ".${ext}". Please upload a receipt image (JPEG, PNG, PDF, TIFF, BMP, WEBP).`,
        { duration: 5000 }
      );
      return;
    }

    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);

    try {
      const { data } = await api.post("/receipts/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setLastResult(data);
      qc.invalidateQueries({ queryKey: ["receipts"] });
      toast.success(
        data.merchant
          ? `Receipt scanned: ${data.merchant}${ data.total_amount ? ` — INR ${Number(data.total_amount).toLocaleString("en-IN")}` : "" }`
          : "Receipt uploaded. Some fields could not be extracted — please fill them in manually.",
        { duration: 5000 }
      );
    } catch (err: any) {
      // Show the exact error message from the backend
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Upload failed. Please try again.", { duration: 6000 });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Receipts</h1>
          <p className="text-xs text-gray-400 mt-0.5">Supported: JPEG, PNG, PDF, TIFF, BMP, WEBP — max {MAX_MB} MB</p>
        </div>
        <label className={`btn-primary flex items-center gap-2 text-sm cursor-pointer ${ uploading ? "opacity-60 pointer-events-none" : "" }`}>
          <Upload size={16} />
          {uploading ? "Scanning..." : "Upload Receipt"}
          <input
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      {/* Last scan result banner */}
      {lastResult && (
        <div className="card border border-blue-200 bg-blue-50">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={16} className="text-blue-600" />
            <p className="font-semibold text-blue-800 text-sm">Last Scan Result</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-500">Merchant</p>
              <p className="font-medium text-gray-800">{lastResult.merchant || "Not detected"}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Amount</p>
              <p className="font-medium text-gray-800">
                {lastResult.total_amount ? `INR ${Number(lastResult.total_amount).toLocaleString("en-IN")}` : "Not detected"}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Date</p>
              <p className="font-medium text-gray-800">{lastResult.receipt_date || "Not detected"}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Tax</p>
              <p className="font-medium text-gray-800">
                {lastResult.tax_amount ? `INR ${Number(lastResult.tax_amount).toLocaleString("en-IN")}` : "—"}
              </p>
            </div>
          </div>
          {lastResult.ocr_raw_text && (
            <div className="mt-3">
              <button
                onClick={() => setExpandedId(expandedId === -1 ? null : -1)}
                className="text-xs text-blue-600 hover:underline flex items-center gap-1"
              >
                {expandedId === -1 ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {expandedId === -1 ? "Hide" : "Show"} raw OCR text
              </button>
              {expandedId === -1 && (
                <pre className="mt-2 text-xs bg-white border border-gray-200 rounded p-3 overflow-auto max-h-40 text-gray-600 whitespace-pre-wrap">
                  {lastResult.ocr_raw_text}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      {receipts.length === 0 ? (
        <div className="card text-center py-12">
          <Upload size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">No receipts yet.</p>
          <p className="text-gray-400 text-xs mt-1">Upload a clear photo of a receipt to extract details automatically.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {receipts.map((r) => (
            <div key={r.id} className="card">
              <div className="flex items-start justify-between">
                <p className="font-semibold text-gray-800">{r.merchant || "Unknown merchant"}</p>
                {r.transaction_id ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Linked</span>
                ) : (
                  <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">Unlinked</span>
                )}
              </div>
              {r.total_amount
                ? <p className="text-xl font-bold text-gray-900 mt-1">{formatINR(Number(r.total_amount))}</p>
                : <p className="text-sm text-gray-400 mt-1">Amount not detected</p>
              }
              <div className="flex gap-4 mt-1">
                {r.receipt_date && <p className="text-xs text-gray-400">{r.receipt_date}</p>}
                {r.tax_amount && <p className="text-xs text-gray-500">Tax: {formatINR(Number(r.tax_amount))}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Categories ────────────────────────────────────────────────────────────────

export function Categories() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset } = useForm<any>();

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => api.get("/categories").then((r) => r.data),
  });

  const saveMutation = useMutation({
    mutationFn: (data: any) => api.post("/categories", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] });
      toast.success("Category created");
      setShowForm(false); reset();
    },
  });

  const system = categories.filter((c) => c.is_system);
  const custom = categories.filter((c) => !c.is_system);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
        <button onClick={() => { reset(); setShowForm(true); }} className="btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Add Category
        </button>
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-800 mb-3">System Categories</h2>
        <div className="flex flex-wrap gap-2">
          {system.map((c) => (
            <span key={c.id} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
              {c.name}
            </span>
          ))}
        </div>
      </div>

      {custom.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-3">Custom Categories</h2>
          <div className="flex flex-wrap gap-2">
            {custom.map((c) => (
              <span key={c.id} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
                {c.name}
              </span>
            ))}
          </div>
        </div>
      )}

      <Dialog open={showForm} onClose={() => setShowForm(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
            <Dialog.Title className="font-semibold text-gray-900 mb-4">New Category</Dialog.Title>
            <form onSubmit={handleSubmit((d) => saveMutation.mutate(d))} className="space-y-3">
              <div>
                <label className="label">Name</label>
                <input {...register("name", { required: true })} className="input" placeholder="e.g. Pet Care" />
              </div>
              <div>
                <label className="label">Parent Category (optional)</label>
                <select {...register("parent_category_id", { valueAsNumber: true })} className="input">
                  <option value="">None</option>
                  {system.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary text-sm">Cancel</button>
                <button type="submit" disabled={saveMutation.isPending} className="btn-primary text-sm">Save</button>
              </div>
            </form>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}
