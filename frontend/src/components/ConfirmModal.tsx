import { X } from "lucide-react";

interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onClose: () => void;
}

// Substitui o `window.confirm()` nativo do navegador por um modal do próprio
// sistema — mesmo padrão do protótipo de referência (ConfirmModal).
export default function ConfirmModal({ title, message, confirmLabel = "Confirmar", onConfirm, onClose }: ConfirmModalProps) {
  return (
    <div
      className="fixed inset-0 bg-brand-navy/40 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-card p-6 w-full max-w-[420px] max-h-[88vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-base font-semibold text-brand-navy m-0">{title}</h3>
          <X size={18} className="cursor-pointer text-neutralState" onClick={onClose} />
        </div>
        <p className="text-[13.5px] text-brand-graphite leading-relaxed">{message}</p>
        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-btn bg-white border border-borderMuted px-4 py-2 text-sm font-medium text-brand-graphite"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-btn bg-danger text-white px-4 py-2 text-sm font-medium"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
