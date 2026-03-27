import React from "react";
import { cn } from "../../../lib/utils";
import { Shield, Fuel, Zap, Settings2 } from "lucide-react";

interface ServiceCostMeterProps {
  totalMultiplier: number;
  multipliers: {
    brand: number;
    fuel: number;
    drive: number;
    gearbox: number;
  };
  mode?: "gauge" | "flat";
  className?: string;
}

type StatusColors = {
  text: string;
  bg: string;
  border: string;
  glow: string;
  gradient: string;
};

export function ServiceCostMeter({ 
  totalMultiplier, 
  multipliers, 
  mode = "gauge",
  className 
}: ServiceCostMeterProps) {
  const deviationPct = Math.round((totalMultiplier - 1.0) * 100);
  const displayDeviation = Math.max(-100, Math.min(100, deviationPct));
  
  // Angle for gauge: -90 (taniej) to +90 (drożej)
  // We'll map -50% to -90deg and +50% to +90deg
  const angle = Math.max(-90, Math.min(90, (displayDeviation / 50) * 90));

  const getStatusColors = (val: number): StatusColors => {
    if (val > 15) return { 
      text: "text-rose-500", 
      bg: "bg-rose-500", 
      border: "border-rose-200", 
      glow: "shadow-[0_0_15px_-3px_rgba(244,63,94,0.4)]",
      gradient: "from-rose-400 to-rose-600"
    };
    if (val > 5) return { 
      text: "text-amber-500", 
      bg: "bg-amber-500", 
      border: "border-amber-200", 
      glow: "shadow-[0_0_15px_-3px_rgba(245,158,11,0.4)]",
      gradient: "from-amber-400 to-amber-600"
    };
    if (val < -5) return { 
      text: "text-emerald-500", 
      bg: "bg-emerald-500", 
      border: "border-emerald-200", 
      glow: "shadow-[0_0_15px_-3px_rgba(16,185,129,0.4)]",
      gradient: "from-emerald-400 to-emerald-600"
    };
    return { 
      text: "text-slate-400", 
      bg: "bg-slate-400", 
      border: "border-slate-200", 
      glow: "",
      gradient: "from-slate-300 to-slate-500"
    };
  };

  const colors = getStatusColors(deviationPct);

  if (mode === "flat") {
    return (
      <div className={cn("flex items-center gap-2 group cursor-help", className)} title={`Wskaźnik kosztowości: ${deviationPct > 0 ? '+' : ''}${deviationPct}%`}>
         <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter opacity-70 group-hover:opacity-100 transition-opacity">Srv</span>
         
         <div className="relative w-16 h-1.5 flex items-center">
            {/* The Gradient Track: Green (Tanie) -> Gray (Center) -> Red (Drogie) */}
            <div className="absolute inset-0 bg-slate-100 rounded-full overflow-hidden border border-slate-200/50">
               <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 via-slate-200 to-rose-500 opacity-40" />
               {/* Center tick for 1.0 baseline */}
               <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-slate-400/50 z-10" />
            </div>
            
            {/* Indicator Knob: Floating pill that glows */}
            <div 
              className={cn(
                "absolute h-3 w-1 rounded-full z-20 transition-all duration-700 ease-in-out shadow-sm ring-1 ring-white/50",
                colors.bg
              )}
              style={{
                left: `calc(${50 + (displayDeviation / 2)}% - 2px)`,
              }}
            />
         </div>

         {/* Only show percentage on hover or very subtly */}
         <span className={cn(
           "text-[10px] font-bold tabular-nums transition-opacity duration-300 opacity-0 group-hover:opacity-100",
           colors.text
         )}>
           {deviationPct > 0 ? `+${deviationPct}%` : `${deviationPct}%`}
         </span>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col items-center p-6 bg-white rounded-2xl border border-slate-200 shadow-xl relative overflow-hidden group", className)}>
      {/* Background decoration */}
      <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 bg-slate-50 rounded-full blur-3xl opacity-50 group-hover:opacity-100 transition-opacity" />
      
      <div className="w-full flex justify-between items-center mb-6">
        <div className="flex flex-col">
          <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Impact Meter</h5>
          <span className="text-xs font-bold text-slate-700">Wskaźnik Kosztowości</span>
        </div>
        <div className={cn(
          "px-3 py-1 rounded-full text-xs font-black border shadow-sm transition-all animate-in zoom-in duration-500",
          colors.text, colors.bg.replace("bg-", "bg-").replace("500", "50"), colors.border
        )}>
          {deviationPct > 0 ? "WYŻSZY KOSZT" : deviationPct < 0 ? "OSZCZĘDNOŚĆ" : "STANDARD"}
        </div>
      </div>

      <div className="relative w-56 h-32 flex flex-col items-center">
        {/* The Gauge SVG */}
        <svg viewBox="0 0 100 50" className="w-full">
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="50%" stopColor="#f5f5f5" />
              <stop offset="100%" stopColor="#f43f5e" />
            </linearGradient>
          </defs>
          {/* Background Track */}
          <path
            d="M 10 45 A 40 40 0 0 1 90 45"
            fill="none"
            stroke="#f1f5f9"
            strokeWidth="8"
            strokeLinecap="round"
          />
          {/* Gradient Track */}
          <path
            d="M 10 45 A 40 40 0 0 1 90 45"
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth="8"
            strokeLinecap="round"
            opacity="0.1"
          />
          
          {/* Active Segment (Subtle line) */}
          <path
             d={deviationPct >= 0 
               ? `M 50 45 A 40 40 0 0 1 ${50 + 40 * Math.sin((angle * Math.PI) / 180)} ${45 - 40 * Math.cos((angle * Math.PI) / 180)}`
               : `M ${50 + 40 * Math.sin((angle * Math.PI) / 180)} ${45 - 40 * Math.cos((angle * Math.PI) / 180)} A 40 40 0 0 1 50 45`
             }
             fill="none"
             stroke={deviationPct === 0 ? "transparent" : (deviationPct > 0 ? "#f43f5e" : "#10b981")}
             strokeWidth="8"
             strokeLinecap="round"
             className="transition-all duration-1000 ease-out"
          />

          {/* Scale Labels */}
          <text x="5" y="49" fontSize="3" fill="#94a3b8" fontWeight="bold">-50%</text>
          <text x="47" y="3" fontSize="4" fill="#64748b" fontWeight="black">OK</text>
          <text x="88" y="49" fontSize="3" fill="#94a3b8" fontWeight="bold">+50%</text>
        </svg>

        {/* Center Display */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
           <div className={cn("text-4xl font-black tracking-tight tabular-nums transition-all duration-700", colors.text)}>
              {deviationPct > 0 ? `+${deviationPct}%` : `${deviationPct}%`}
           </div>
           <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest -mt-1">vs Baseline</p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 w-full mt-8">
        <DNSCard icon={<Shield className="w-4 h-4" />} label="Marka" val={multipliers.brand} color={getStatusColors(Math.round((multipliers.brand - 1) * 100))} />
        <DNSCard icon={<Fuel className="w-4 h-4" />} label="Paliwo" val={multipliers.fuel} color={getStatusColors(Math.round((multipliers.fuel - 1) * 100))} />
        <DNSCard icon={<Zap className="w-4 h-4" />} label="Napęd" val={multipliers.drive} color={getStatusColors(Math.round((multipliers.drive - 1) * 100))} />
        <DNSCard icon={<Settings2 className="w-4 h-4" />} label="Skrzynia" val={multipliers.gearbox} color={getStatusColors(Math.round((multipliers.gearbox - 1) * 100))} />
      </div>
    </div>
  );
}

function DNSCard({ icon, label, val, color }: { icon: React.ReactNode, label: string, val: number, color: StatusColors }) {
  const dev = Math.round((val - 1) * 100);
  return (
    <div className="flex flex-col items-center gap-2 px-2 py-3 bg-slate-50/50 rounded-xl border border-slate-100 transition-all hover:bg-white hover:shadow-md hover:scale-105">
      <div className={cn("p-2 rounded-lg bg-white border border-slate-200 shadow-sm", color.text)}>
        {icon}
      </div>
      <div className="flex flex-col items-center">
        <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
        <span className={cn("text-[10px] font-black tabular-nums", color.text)}>
          {dev > 0 ? `+${dev}%` : dev < 0 ? `${dev}%` : "—"}
        </span>
      </div>
    </div>
  );
}
