import { useState } from "react";
import { UploadCloud } from "lucide-react";
import {
  Box,
  Typography,
  Paper,
  ButtonBase,
  useTheme,
  alpha,
} from "@mui/material";

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
}

export function UploadZone({ onFilesSelected }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const theme = useTheme();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(Array.from(e.target.files));
    }
  };

  return (
    <Box sx={{ w: "100%", mb: 3 }}>
      <ButtonBase
        component="label"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          width: "100%",
          display: "block",
          textAlign: "left",
          borderRadius: 3,
        }}
      >
        <Paper
          variant="outlined"
          sx={{
            py: 4,
            px: 5,
            borderRadius: 3,
            border: "2px dashed",
            borderColor: isDragging
              ? "primary.main"
              : theme.palette.mode === "light"
              ? "divider"
              : alpha(theme.palette.divider, 0.2),
            bgcolor: isDragging
              ? alpha(theme.palette.primary.main, 0.05)
              : theme.palette.mode === "light"
              ? alpha(theme.palette.background.paper, 0.6)
              : alpha(theme.palette.background.paper, 0.3),
            backdropFilter: "blur(8px)",
            transition: "all 0.3s ease",
            "&:hover": {
              borderColor: "primary.main",
              bgcolor: alpha(theme.palette.primary.main, 0.02),
              transform: "translateY(-2px)",
              boxShadow: theme.shadows[4],
            },
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            alignItems: "center",
            gap: 3,
          }}
        >
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: isDragging ? "primary.main" : "action.hover",
              color: isDragging ? "primary.contrastText" : "primary.main",
              transition: "all 0.3s ease",
            }}
          >
            <UploadCloud size={28} />
          </Box>

          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Wybierz plik z komputera
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              lub przeciągnij go tutaj • PDF, XLS, XLSX, PNG, JPG do 50 MB
            </Typography>
          </Box>

          <Box
            sx={{
              px: 3,
              py: 1,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "primary.main",
              color: "primary.main",
              fontSize: "0.75rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Prześlij pliki
          </Box>
        </Paper>
        <input
          type="file"
          hidden
          multiple
          accept=".pdf,.xls,.xlsx,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
        />
      </ButtonBase>
    </Box>
  );
}
