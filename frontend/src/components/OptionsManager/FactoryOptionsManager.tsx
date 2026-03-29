import {
  Box,
  Typography,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  IconButton,
} from "@mui/material";
import { Trash2, Plus } from "lucide-react";

import type { FactoryOption } from "../../types";

interface FactoryOptionsManagerProps {
  options: FactoryOption[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onUpdate: (id: number, field: string, value: any) => void;
  onAdd: () => void;
  onRemove: (id: number) => void;
}

export default function FactoryOptionsManager({
  options,
  onUpdate,
  onAdd,
  onRemove,
}: FactoryOptionsManagerProps) {
  return (
    <Box sx={{ p: 2, bgcolor: "#fff", borderBottom: "1px solid #ddd" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold">
          Opcje Fabryczne
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<Plus size={16} />}
          onClick={onAdd}
        >
          Dodaj Opcję Fabryczną
        </Button>
      </Box>

      {options.map((opt) => (
        <Box key={opt.id} sx={{ display: "flex", gap: 2, mb: 1, alignItems: "center", flexWrap: "wrap" }}>
          <Box sx={{ flex: "1 1 250px" }}>
            <TextField
              fullWidth
              size="small"
              label="Nazwa"
              value={opt.name}
              onChange={(e) => onUpdate(opt.id, "name", e.target.value)}
            />
          </Box>
          <Box sx={{ flex: "1 1 120px" }}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Cena Netto"
              value={opt.price_net}
              onChange={(e) => onUpdate(opt.id, "price_net", parseFloat(e.target.value) || 0)}
            />
          </Box>
          <Box sx={{ flex: "1 1 120px" }}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Cena Brutto"
              value={opt.price_gross}
              onChange={(e) => onUpdate(opt.id, "price_gross", parseFloat(e.target.value) || 0)}
            />
          </Box>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={opt.is_non_discountable}
                  onChange={(e) => onUpdate(opt.id, "is_non_discountable", e.target.checked)}
                />
              }
              label="Nierabatowana"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={opt.is_residual_impacting}
                  onChange={(e) => onUpdate(opt.id, "is_residual_impacting", e.target.checked)}
                />
              }
              label="WR"
            />
            <IconButton color="error" onClick={() => onRemove(opt.id)}>
              <Trash2 size={20} />
            </IconButton>
          </Box>
        </Box>
      ))}
      {options.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          Brak opcji fabrycznych.
        </Typography>
      )}
    </Box>
  );
}
