import React, { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export function CollapsibleSection({
  title,
  defaultOpen = true,
  children,
  rightIcon,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-slate-300 rounded mb-4 overflow-hidden bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2 bg-[#2D4A77] text-white hover:bg-[#233a60] transition-colors focus:outline-none"
      >
        <span className="font-bold text-sm tracking-wide">{title}</span>
        <div className="flex items-center gap-2">
          {rightIcon && <span className="text-white/80">{rightIcon}</span>}
          {isOpen ? (
            <ChevronUp className="w-5 h-5 text-white" />
          ) : (
            <ChevronDown className="w-5 h-5 text-white" />
          )}
        </div>
      </button>

      {isOpen && <div className="p-4 bg-white">{children}</div>}
    </div>
  );
}
