import { useState } from "react";
import type { JSX } from "react";

interface NetGrossInputProps {
  netValue: number;
  onChangeNet: (newNet: number) => void;
}

export function NetGrossInput({ netValue, onChangeNet }: NetGrossInputProps): JSX.Element {
  const [localNet, setLocalNet] = useState(netValue.toString());
  const [localGross, setLocalGross] = useState((netValue * 1.23).toFixed(2));
  const [prevNetValue, setPrevNetValue] = useState(netValue);

  if (Math.abs(netValue - prevNetValue) > 0.01) {
    setPrevNetValue(netValue);
    setLocalNet(netValue.toString());
    setLocalGross((netValue * 1.23).toFixed(2));
  }

  const handleNetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalNet(val); // Always keep what user typed
    
    // Parse it allowing comma or dot
    const parsed = val.replace(',', '.');
    // Only update parent and gross if it's a valid number and doesn't end with . or ,
    if (parsed && !parsed.endsWith('.') && !isNaN(Number(parsed))) {
       const num = Number(parsed);
       setLocalGross((num * 1.23).toFixed(2));
       setPrevNetValue(num); // Suppress external sync
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
       setPrevNetValue(net); // Suppress external sync
       onChangeNet(net);
    } else if (val === '') {
       setLocalNet('');
       setPrevNetValue(0);
       onChangeNet(0);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <div className="relative flex items-center">
        <input 
          type="number"
          step="0.01"
          className="w-20 sm:w-24 text-right px-2 py-1.5 border border-slate-200 border-r-0 rounded-l text-slate-800 font-semibold focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 z-10"
          value={localNet}
          onChange={handleNetChange}
          placeholder="0.00"
          title="Kwota Netto"
        />
        <div className="bg-slate-50 border border-slate-200 rounded-r px-1.5 sm:px-2 py-1.5 text-xs font-bold text-slate-500 uppercase flex items-center h-[34px]">
          Netto
        </div>
      </div>
      <span className="text-slate-300 font-bold mx-0.5">=</span>
      <div className="relative flex items-center">
        <input 
          type="number"
          step="0.01"
          className="w-20 sm:w-24 text-right px-2 py-1.5 border border-slate-200 border-r-0 rounded-l text-slate-800 font-semibold focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 z-10"
          value={localGross}
          onChange={handleGrossChange}
          placeholder="0.00"
          title="Kwota Brutto"
        />
        <div className="bg-slate-50 border border-slate-200 rounded-r px-1.5 sm:px-2 py-1.5 text-xs font-bold text-slate-500 uppercase flex items-center h-[34px]">
          Brutto
        </div>
      </div>
      <span className="text-slate-400 font-medium ml-1 mr-2 hidden sm:inline">PLN</span>
    </div>
  );
}
