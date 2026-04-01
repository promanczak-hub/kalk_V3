import { useState } from "react";
import type { JSX } from "react";

interface NetGrossInputProps {
  netValue: number;
  onChangeNet: (newNet: number) => void;
}

export function NetGrossInput({ netValue, onChangeNet }: NetGrossInputProps): JSX.Element {
  const [localNet, setLocalNet] = useState((netValue ?? 0).toString());
  const [localGross, setLocalGross] = useState(((netValue ?? 0) * 1.23).toFixed(2));
  const [prevNetValue, setPrevNetValue] = useState(netValue ?? 0);

  if (Math.abs((netValue ?? 0) - prevNetValue) > 0.01) {
    setPrevNetValue(netValue ?? 0);
    setLocalNet((netValue ?? 0).toString());
    setLocalGross(((netValue ?? 0) * 1.23).toFixed(2));
  }

  const handleNetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalNet(val); 
    const parsed = val.replace(',', '.');
    if (parsed && !parsed.endsWith('.') && !isNaN(Number(parsed))) {
       const num = Number(parsed);
       setLocalGross((num * 1.23).toFixed(2));
       setPrevNetValue(num); 
       onChangeNet(num);
    } else if (val === '') {
       setLocalGross('');
       setPrevNetValue(0);
       onChangeNet(0);
    }
  };

  const handleGrossChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalGross(val);
    const parsed = val.replace(',', '.');
    if (parsed && !parsed.endsWith('.') && !isNaN(Number(parsed))) {
       const num = Number(parsed);
       const net = num / 1.23;
       setLocalNet(net.toFixed(2));
       setPrevNetValue(net); 
       onChangeNet(net);
    } else if (val === '') {
       setLocalNet('');
       setPrevNetValue(0);
       onChangeNet(0);
    }
  };

  return (
    <div className="flex items-center justify-between w-full gap-2">
      <div className="relative flex-1 min-w-[90px]">
        <input
          type="number"
          className="w-full px-2 pr-9 py-1.5 border border-slate-200 rounded text-slate-700 font-medium text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          value={localNet}
          onChange={handleNetChange}
          placeholder="Netto"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <span className="text-[10px] font-medium text-slate-400">PLN</span>
        </div>
      </div>
      
      <span className="text-[11px] font-bold text-slate-300">=</span>

      <div className="relative flex-1 min-w-[90px]">
        <input
          type="number"
          className="w-full px-2 pr-9 py-1.5 border border-slate-200 rounded text-slate-700 font-medium text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-slate-50"
          value={localGross}
          onChange={handleGrossChange}
          placeholder="Brutto"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <span className="text-[10px] font-medium text-slate-400">PLN</span>
        </div>
      </div>
    </div>
  );
}
