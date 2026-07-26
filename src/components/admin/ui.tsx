import type { ReactNode } from "react";

export function Card({ title, action, children, className = "" }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl border border-stone-200 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100">
          <div className="font-medium text-stone-800">{title}</div>
          <div>{action}</div>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Stat({ label, value, hint, tone = "default" }: { label: string; value: string | number; hint?: string; tone?: "default" | "up" | "down" }) {
  const toneClass = tone === "up" ? "text-emerald-600" : tone === "down" ? "text-red-600" : "text-stone-500";
  return (
    <div className="bg-white rounded-xl border border-stone-200 p-5">
      <div className="text-xs uppercase tracking-wide text-stone-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-stone-900">{value}</div>
      {hint && <div className={`mt-1 text-xs ${toneClass}`}>{hint}</div>}
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <div className="text-xs font-medium text-stone-600 mb-1">{label}</div>
      {children}
      {hint && <div className="text-[11px] text-stone-400 mt-1">{hint}</div>}
    </label>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`w-full h-10 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none text-sm ${props.className ?? ""}`} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`w-full px-3 py-2 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none text-sm ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`w-full h-10 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none text-sm bg-white ${props.className ?? ""}`} />;
}

export function Button({ variant = "primary", ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" | "outline" }) {
  const base = "inline-flex items-center justify-center gap-1.5 h-9 px-3.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50";
  const styles = {
    primary: "bg-stone-900 text-white hover:bg-stone-800",
    ghost: "text-stone-600 hover:bg-stone-100",
    danger: "bg-red-600 text-white hover:bg-red-700",
    outline: "border border-stone-300 text-stone-700 hover:bg-stone-50",
  }[variant];
  return <button {...p} className={`${base} ${styles} ${p.className ?? ""}`} />;
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <label className="inline-flex items-center gap-2 cursor-pointer">
      <span className={`relative inline-block w-9 h-5 rounded-full transition-colors ${checked ? "bg-emerald-500" : "bg-stone-300"}`}>
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? "transtone-x-4" : "transtone-x-0.5"}`} />
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="sr-only" />
      </span>
      {label && <span className="text-sm text-stone-700">{label}</span>}
    </label>
  );
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "success" | "warn" | "danger" | "info" }) {
  const map = {
    default: "bg-stone-100 text-stone-700",
    success: "bg-emerald-100 text-emerald-700",
    warn: "bg-amber-100 text-amber-700",
    danger: "bg-red-100 text-red-700",
    info: "bg-sky-100 text-sky-700",
  } as const;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${map[tone]}`}>{children}</span>;
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="text-center py-10 text-stone-500">
      <div className="font-medium text-stone-700">{title}</div>
      {hint && <div className="text-sm mt-1">{hint}</div>}
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl w-full max-w-lg shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <div className="font-medium">{title}</div>
          <button onClick={onClose} className="text-stone-500 hover:text-stone-800">✕</button>
        </div>
        <div className="p-5">{children}</div>
        {footer && <div className="px-5 py-3 border-t bg-stone-50 flex justify-end gap-2 rounded-b-xl">{footer}</div>}
      </div>
    </div>
  );
}
