import React, { useRef, useState } from "react";
import {
  Box,
  Typography,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  IconButton,
  CircularProgress,
  Alert,
} from "@mui/material";
import { Trash2, Plus } from "lucide-react";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import axios from "axios";

interface ExtractedServiceOption {
  name: string;
  net_price: number;
  description_or_components: string[];
  effects: {
    override_samar_class?: string;
    override_homologation?: string;
    adds_weight_kg?: number;
    is_financial_only: boolean;
  } | null;
}

interface Option {
  Id: number;
  Nazwa: string;
  CenaNetto: number;
  Cena: number;
  isNierabatowany: boolean;
  WR: boolean;
}

interface ServiceOptionsManagerProps {
  options: Option[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onUpdate: (id: number, field: string, value: any) => void;
  onAdd: () => void;
  onRemove: (id: number) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onAddExtracted?: (extracted: any) => void;
}

export default function ServiceOptionsManager({
  options,
  onUpdate,
  onAdd,
  onRemove,
  onAddExtracted,
}: ServiceOptionsManagerProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setErrorMsg(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post<ExtractedServiceOption>(
        "http://127.0.0.1:8000/api/extract/service-option",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      if (response.data && onAddExtracted) {
        onAddExtracted(response.data);
      }
    } catch (error: unknown) {
      console.error("Error extracting service option:", error);
      let errMsg = "Wystąpił błąd podczas analizy pliku.";
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        errMsg = error.response.data.detail;
      } else if (error instanceof Error) {
        errMsg = error.message;
      }
      setErrorMsg(errMsg);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <Box sx={{ p: 2, bgcolor: "#fff", borderBottom: "1px solid #ddd" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2, flexWrap: "wrap", gap: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold">
          Opcje Serwisowe i Akcesoria
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<Plus size={16} />}
            onClick={onAdd}
          >
            Dodaj Usługę
          </Button>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            style={{ display: "none" }}
            ref={fileInputRef}
            onChange={handleFileChange}
          />
          <Button
            variant="contained"
            size="small"
            color="secondary"
            startIcon={isUploading ? <CircularProgress size={16} color="inherit" /> : <AutoFixHighIcon fontSize="small" />}
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || !onAddExtracted}
            sx={{ whiteSpace: "nowrap" }}
          >
            {isUploading ? "Analizuję..." : "Z PDF (AI)"}
          </Button>
        </Box>
      </Box>

      {errorMsg && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorMsg}
        </Alert>
      )}

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
          Brak usług dodatkowych.
        </Typography>
      )}
    </Box>
  );
}
