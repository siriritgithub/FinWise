import { Dialog } from "@headlessui/react";
import { AlertTriangle } from "lucide-react";

interface Props {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel, loading }: Props) {
  return (
    <Dialog open={open} onClose={onCancel} className="relative z-50">
      <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="bg-[#111a2b] border border-white/10 rounded-2xl shadow-2xl shadow-black/40 p-6 max-w-sm w-full text-slate-100">
          <div className="flex items-center gap-3 mb-3">
            <AlertTriangle className="text-red-500" size={22} />
            <Dialog.Title className="font-semibold text-white">{title}</Dialog.Title>
          </div>
          <p className="text-sm text-slate-400 mb-5">{message}</p>
          <div className="flex gap-3 justify-end">
            <button onClick={onCancel} className="btn-secondary text-sm">Cancel</button>
            <button
              onClick={onConfirm}
              disabled={loading}
              className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
            >
              {loading ? "Deleting..." : "Delete"}
            </button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
}
