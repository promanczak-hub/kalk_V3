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

interface Option {
  Id: number;
  Nazwa: string;
  CenaNetto: number;
  Cena: number;
  isNierabatowany: boolean;
  WR: boolean;
}

interface FactoryOptionsManagerProps {
  options: Option[];
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
        <Box key={opt.Id} sx={{ display: "flex", gap: 2, mb: 1, alignItems: "center", flexWrap: "wrap" }}>
          <Box sx={{ flex: "1 1 250px" }}>
            <TextField
              fullWidth
              size="small"
              label="Nazwa"
              value={opt.Nazwa}
              onChange={(e) => onUpdate(opt.Id, "Nazwa", e.target.value)}
            />
          </Box>
          <Box sx={{ flex: "1 1 120px" }}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Cena Netto"
              value={opt.CenaNetto}
              onChange={(e) => onUpdate(opt.Id, "CenaNetto", parseFloat(e.target.value) || 0)}
            />
          </Box>
          <Box sx={{ flex: "1 1 120px" }}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Cena Brutto"
              value={opt.Cena}
              onChange={(e) => onUpdate(opt.Id, "Cena", parseFloat(e.target.value) || 0)}
            />
          </Box>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={opt.isNierabatowany}
                  onChange={(e) => onUpdate(opt.Id, "isNierabatowany", e.target.checked)}
                />
              }
              label="Nierabatowana"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={opt.WR}
                  onChange={(e) => onUpdate(opt.Id, "WR", e.target.checked)}
                />
              }
              label="WR"
            />
            <IconButton color="error" onClick={() => onRemove(opt.Id)}>
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
