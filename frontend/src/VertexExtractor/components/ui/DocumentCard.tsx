import {
  Card,
  CardContent,
  Typography,
  Box,
  IconButton,
  LinearProgress,
  Chip,
  alpha,
  useTheme,
} from "@mui/material";
import {
  FileText,
  FileSpreadsheet,
  X,
  CheckCircle2,
  ChevronRight,
  AlertCircle,
} from "lucide-react";
import type { UploadedDocument } from "../../types";

export function DocumentCard({
  doc,
  onOpenJson,
  onRemove,
}: {
  doc: UploadedDocument;
  onOpenJson: () => void;
  onRemove?: () => void;
}) {
  const isExcel = doc.type === "excel";
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";

  return (
    <Card
      sx={{
        borderRadius: 4,
        position: "relative",
        overflow: "hidden",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "&:hover": {
          transform: "translateY(-6px)",
          boxShadow: isDark 
            ? "0 12px 24px rgba(0,0,0,0.4)" 
            : "0 12px 24px rgba(0,0,0,0.1)",
          "& .document-icon-box": {
            transform: "scale(1.1) rotate(-5deg)",
          },
        },
        bgcolor: isDark ? alpha(theme.palette.background.paper, 0.4) : alpha(theme.palette.background.paper, 0.8),
        backdropFilter: "blur(12px)",
        border: "1px solid",
        borderColor: isDark ? alpha("#ffffff", 0.08) : alpha("#000000", 0.05),
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 200,
      }}
    >
      {/* Remove Button */}
      {onRemove && (
        <IconButton
          size="small"
          aria-label="Usuń dokument"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          sx={{
            position: "absolute",
            top: 8,
            right: 8,
            zIndex: 2,
            opacity: 0.6,
            "&:hover": { opacity: 1, bgcolor: alpha(theme.palette.error.main, 0.1) },
          }}
        >
          <X size={16} />
        </IconButton>
      )}

      <CardContent
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          flexGrow: 1,
          pt: 4,
        }}
      >
        <Box
          className="document-icon-box"
          sx={{
            width: 64,
            height: 64,
            borderRadius: 3,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            mb: 2,
            transition: "all 0.4s ease",
            bgcolor: isExcel 
              ? alpha(theme.palette.success.main, 0.1) 
              : alpha(theme.palette.error.main, 0.1),
            color: isExcel ? "success.main" : "error.main",
            position: "relative",
          }}
        >
          {isExcel ? <FileSpreadsheet size={32} /> : <FileText size={32} />}
          
          {doc.status === "completed" && (
            <Box
              sx={{
                position: "absolute",
                bottom: -6,
                right: -6,
                bgcolor: "background.paper",
                borderRadius: "50%",
                lineHeight: 0,
                boxShadow: theme.shadows[2],
              }}
            >
              <CheckCircle2 size={20} className="text-emerald-500 fill-emerald-50" />
            </Box>
          )}
        </Box>

        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 700,
            width: "100%",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            mb: 1,
          }}
          title={doc.name}
        >
          {doc.name}
        </Typography>

        {/* Status Indicators */}
        <Box sx={{ width: "100%", mt: "auto" }}>
          {doc.status === "processing" && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" sx={{ color: "primary.main", fontWeight: 700, mb: 1, display: "block" }}>
                AI ANALIZA...
              </Typography>
              <LinearProgress
                sx={{
                  height: 6,
                  borderRadius: 3,
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 3,
                    background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.primary.light})`,
                  },
                }}
              />
            </Box>
          )}

          {doc.status === "uploading" && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" sx={{ color: "warning.main", fontWeight: 700, mb: 1, display: "block" }}>
                WGRYWANIE...
              </Typography>
              <LinearProgress color="warning" sx={{ height: 4, borderRadius: 2 }} />
            </Box>
          )}

          {doc.status === "completed" && (
            <Box
              component="button"
              onClick={onOpenJson}
              sx={{
                mt: 2,
                width: "100%",
                py: 1,
                bgcolor: alpha(theme.palette.primary.main, 0.05),
                border: "none",
                borderRadius: 2,
                color: "primary.main",
                fontSize: "0.75rem",
                fontWeight: 800,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 0.5,
                cursor: "pointer",
                transition: "all 0.2s ease",
                "&:hover": {
                  bgcolor: alpha(theme.palette.primary.main, 0.1),
                  transform: "scale(1.02)",
                },
              }}
            >
              JSON ZAPISANY
              <ChevronRight size={14} />
            </Box>
          )}

          {doc.status === "error" && (
            <Chip
              icon={<AlertCircle size={14} />}
              label="BŁĄD ANALIZY"
              color="error"
              size="small"
              onClick={onOpenJson}
              sx={{ width: "100%", mt: 2, cursor: "pointer" }}
            />
          )}

          {doc.status === "idle" && (
            <Chip label="W KOLEJCE" variant="outlined" size="small" sx={{ mt: 2, opacity: 0.6 }} />
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
