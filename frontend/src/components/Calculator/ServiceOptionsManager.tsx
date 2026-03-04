import React, { useRef, useState } from "react";
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  Paper,
  Alert,
} from "@mui/material";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import axios from "axios";

export interface ExtractedServiceOption {
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

interface ServiceOptionsManagerProps {
  onOptionExtracted: (option: ExtractedServiceOption) => void;
}

export const ServiceOptionsManager: React.FC<ServiceOptionsManagerProps> = ({
  onOptionExtracted,
}) => {
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

      if (response.data) {
        onOptionExtracted(response.data);
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
      // Reset input so the same file can be uploaded again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 2, border: "1px dashed #ccc", bgcolor: "#fafafa" }}>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography variant="subtitle1" fontWeight="bold">
            Dodaj Opcję Serwisową z pliku (Digital Twin)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Wgraj ofertę PDF zabudowy, akcesoriów lub wycenę serwisową. 
            AI automatycznie zinterpretuje koszt układu, jego składniki oraz ewentualny
            wpływ na parametry homologacyjne auta.
          </Typography>
        </Box>
        <Box>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            style={{ display: "none" }}
            ref={fileInputRef}
            onChange={handleFileChange}
          />
          <Button
            variant="contained"
            color="secondary"
            startIcon={isUploading ? <CircularProgress size={20} color="inherit" /> : <AutoFixHighIcon />}
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            sx={{ whiteSpace: "nowrap" }}
          >
            {isUploading ? "Analizuję (Gemini)..." : "Wgraj i Analizuj"}
          </Button>
        </Box>
      </Box>

      {errorMsg && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {errorMsg}
        </Alert>
      )}
    </Paper>
  );
};
