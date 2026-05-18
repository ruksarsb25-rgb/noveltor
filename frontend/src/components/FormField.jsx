import React from "react";

export function FormField({ label, error, hint, children, required }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-slate-700">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-slate-400">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`border border-slate-300 rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0F3557]/30 focus:border-[#0F3557] ${className}`}
      {...props}
    />
  );
}

export function Textarea({ className = "", ...props }) {
  return (
    <textarea
      className={`border border-slate-300 rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0F3557]/30 focus:border-[#0F3557] resize-y min-h-[80px] ${className}`}
      {...props}
    />
  );
}

export function Select({ options = [], className = "", ...props }) {
  return (
    <select
      className={`border border-slate-300 rounded-md px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0F3557]/30 focus:border-[#0F3557] bg-white ${className}`}
      {...props}
    >
      {options.map((opt) => (
        <option key={opt.value ?? opt} value={opt.value ?? opt}>
          {opt.label ?? opt}
        </option>
      ))}
    </select>
  );
}

export function Button({ variant = "primary", className = "", children, ...props }) {
  const base = "inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-[#0F3557] text-white hover:bg-[#0a2540]",
    secondary: "border border-slate-300 text-slate-700 hover:bg-slate-50",
    danger: "bg-red-600 text-white hover:bg-red-700",
    ghost: "text-slate-600 hover:bg-slate-100",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function Card({ className = "", children, ...props }) {
  return (
    <div className={`bg-white rounded-lg border border-slate-200 shadow-sm ${className}`} {...props}>
      {children}
    </div>
  );
}

export function Badge({ color = "blue", children }) {
  const colors = {
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
    red: "bg-red-100 text-red-700",
    yellow: "bg-yellow-100 text-yellow-700",
    slate: "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[color]}`}>
      {children}
    </span>
  );
}
