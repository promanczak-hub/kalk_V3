import React from 'react';
import { Info, TrendingDown, TrendingUp } from 'lucide-react';

export const CostRow = ({ label, original, expert, diff, formatter = (v: number) => v.toFixed(2) }: { label: string, original: number, expert: number, diff: number, formatter?: (v: number) => string | React.ReactNode }) => (
  <div className="flex justify-between items-center text-sm py-1 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
    <span className="text-gray-600 w-1/3">{label}</span>
    <div className="flex w-2/3 justify-between items-center">
      <div className="flex flex-col items-end w-1/2 pr-2 border-r border-gray-200">
        <span className="text-xs text-gray-400">Standard</span>
        <span className="font-medium text-gray-700">{formatter(original)}</span>
      </div>
      <div className="flex flex-col items-end w-1/2 pl-2 relative">
        <span className="text-xs text-blue-400 font-medium">Ekspert</span>
        <span className={`font-medium ${expert !== original ? 'text-blue-600' : 'text-gray-700'}`}>
          {formatter(expert)}
        </span>
        {diff !== 0 && (
          <div className={`absolute -right-6 top-1/2 -translate-y-1/2 flex items-center text-xs ${diff > 0 ? 'text-green-500' : 'text-red-500'}`} title={`Różnica: ${diff > 0 ? '+' : ''}${formatter(diff)}`}>
            {diff > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          </div>
        )}
      </div>
    </div>
  </div>
);

export const ExpertNumber = ({ label, value, onChange, placeholder = "", disabled = false, tooltip = "", step, min, suffix }: { label: string, value: number | "", onChange: (v: number | "") => void, placeholder?: string, disabled?: boolean, tooltip?: string, step?: number | string, min?: number, suffix?: string }) => (
  <div className="flex flex-col gap-1">
    <label className="text-xs font-medium text-gray-600 flex items-center gap-1">
      {label}
      {tooltip && <div title={tooltip}><Info className="w-3 h-3 text-gray-400 cursor-help" /></div>}
    </label>
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
      placeholder={placeholder}
      disabled={disabled}
      className="w-full text-sm p-1.5 pr-8 border border-gray-200 rounded focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400 outline-none transition-shadow"
      step={step ?? "any"}
      min={min}
    />
    {suffix && <span className="absolute right-2 top-1/2 translate-y-2 text-[10px] text-gray-400">{suffix}</span>}
  </div>
);

export const ExpertToggle = ({ label, checked, onChange, disabled = false, tooltip = "" }: { label: string, checked: boolean, onChange: (v: boolean) => void, disabled?: boolean, tooltip?: string }) => (
  <div className="flex items-center justify-between p-2 border border-gray-200 rounded hover:bg-gray-50 transition-colors">
    <label className="text-xs font-medium text-gray-600 cursor-pointer flex items-center gap-1 select-none">
      {label}
      {tooltip && <div title={tooltip}><Info className="w-3 h-3 text-gray-400 cursor-help" /></div>}
    </label>
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      disabled={disabled}
      className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 cursor-pointer disabled:cursor-not-allowed"
    />
  </div>
);

export const ExpertSelect = ({ label, value, onChange, options, disabled = false, tooltip = "" }: { label: string, value: string, onChange: (v: string) => void, options: { value: string, label: string }[], disabled?: boolean, tooltip?: string }) => (
  <div className="flex flex-col gap-1">
    <label className="text-xs font-medium text-gray-600 flex items-center gap-1">
      {label}
      {tooltip && <div title={tooltip}><Info className="w-3 h-3 text-gray-400 cursor-help" /></div>}
    </label>
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="w-full text-sm p-1.5 border border-gray-200 rounded focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400 outline-none bg-white transition-shadow"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  </div>
);
