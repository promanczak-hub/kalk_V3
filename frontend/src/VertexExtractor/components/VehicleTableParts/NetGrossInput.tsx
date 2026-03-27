import { useState } from "react";
import type { JSX } from "react";
import { Box, TextField, Typography, InputAdornment } from "@mui/material";

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
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <TextField
        size="small"
        label="Netto"
        type="number"
        value={localNet}
        onChange={handleNetChange}
        sx={{ width: 160 }}
        slotProps={{
          input: {
            style: { fontWeight: 900 },
            endAdornment: <InputAdornment position="end">PLN</InputAdornment>
          }
        }}
      />
      
      <Typography sx={{ fontWeight: 900, color: 'text.disabled' }}>=</Typography>

      <TextField
        size="small"
        label="Brutto"
        type="number"
        value={localGross}
        onChange={handleGrossChange}
        sx={{ width: 160 }}
        slotProps={{
          input: {
            style: { fontWeight: 900 },
            endAdornment: <InputAdornment position="end">PLN</InputAdornment>
          }
        }}
      />
    </Box>
  );
}
