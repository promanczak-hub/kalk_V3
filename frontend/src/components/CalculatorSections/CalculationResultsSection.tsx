import {
  Box,
  Typography,
  Paper,
  Divider,
  Grid,
  Chip,
  Tooltip,
} from "@mui/material";
import {
  CheckCircle2,
  Info,
  Calculator,
  TrendingUp,
  History,
} from "lucide-react";
import type { CalculationResult, CalculationStep } from "../../hooks/useCalculator";

interface CalculationResultsSectionProps {
  result: CalculationResult | null;
  isCalculating: boolean;
}

export default function CalculationResultsSection({
  result,
  isCalculating,
}: CalculationResultsSectionProps) {
  if (isCalculating) {
    return (
      <Paper sx={{ p: 4, textAlign: "center", borderRadius: "16px", border: "1px dashed rgba(0,0,0,0.1)" }}>
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
          <Box sx={{ position: "relative", width: 40, height: 40, borderRadius: "50%", border: "3px solid rgba(0,0,0,0.1)", borderTopColor: "primary.main", animation: "spin 1s linear infinite" }} />
          <Typography variant="h6" color="text.secondary">Trwa obliczanie 12 kroków LTR...</Typography>
          <Typography variant="body2" color="text.secondary">Łączenie danych SAMAR, Matryc Opon i Kosztów Serwisowych</Typography>
        </Box>
        <style>{`
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `}</style>
      </Paper>
    );
  }

  if (!result) {
    return (
      <Paper sx={{ p: 4, textAlign: "center", borderRadius: "16px", bgcolor: "rgba(0,0,0,0.01)" }}>
        <Calculator size={48} color="#94a3b8" style={{ marginBottom: "16px" }} />
        <Typography variant="h6" color="text.secondary">Gotowy do obliczeń</Typography>
        <Typography variant="body2" color="text.secondary">Uzupełnij dane pojazdu i kliknij 'Przelicz 12 Kroków LTR'</Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* FINAL RENT CARD */}
      <Paper 
        elevation={0}
        sx={{ 
          p: 4, 
          borderRadius: "16px", 
          bgcolor: "primary.main", 
          color: "white",
          mb: 4,
          position: "relative",
          overflow: "hidden",
          boxShadow: "0 20px 25px -5px rgba(59, 130, 246, 0.4)"
        }}
      >
        <Box sx={{ position: "absolute", top: -20, right: -20, opacity: 0.1 }}>
          <TrendingUp size={160} />
        </Box>
        
        <Grid container alignItems="center">
          <Grid size={{ xs: 12, md: 7 }}>
            <Typography variant="overline" sx={{ letterSpacing: 2, opacity: 0.9 }}>MIESIĘCZNA RATA WYNAJMU (LTR)</Typography>
            <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
              <Typography variant="h2" sx={{ fontWeight: 800 }}>
                {result.total_rent.toLocaleString('pl-PL', { minimumFractionDigits: 2 })}
              </Typography>
              <Typography variant="h5" sx={{ opacity: 0.8 }}>PLN netto</Typography>
            </Box>
            <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
              <Chip label="Kontrakt Full Service" size="small" sx={{ color: "white", borderColor: "rgba(255,255,255,0.3)", border: "1px solid" }} />
              <Chip label="Gwarancja Ceny" size="small" sx={{ color: "white", borderColor: "rgba(255,255,255,0.3)", border: "1px solid" }} />
            </Box>
          </Grid>
          <Grid size={{ xs: 12, md: 5 }} sx={{ mt: { xs: 3, md: 0 } }}>
            <Paper sx={{ bgcolor: "rgba(255,255,255,0.1)", p: 2, borderRadius: "12px", border: "1px solid rgba(255,255,255,0.2)" }}>
              <Typography variant="body2" sx={{ mb: 1, opacity: 0.8 }}>Podsumowanie Cen:</Typography>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                <Typography variant="body2">Cena Cennikowa:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{result.summary?.base_price_net.toLocaleString()} PLN</Typography>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                <Typography variant="body2">Suma Rabatu:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>-{result.summary?.total_discount_net.toLocaleString()} PLN</Typography>
              </Box>
              <Divider sx={{ my: 1, borderColor: "rgba(255,255,255,0.2)" }} />
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body1">Cena po Rabacie:</Typography>
                <Typography variant="body1" sx={{ fontWeight: 700 }}>{result.summary?.final_price_net.toLocaleString()} PLN</Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Paper>

      {/* 12-STEP TRACE */}
      <Box sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}>
        <History size={18} color="#1e293b" />
        <Typography variant="h6" sx={{ fontWeight: 700 }}>Ślad Rewizyjny (12 Kroków LTR)</Typography>
      </Box>

      {result.steps.map((step: CalculationStep, idx: number) => (
        <Paper 
          key={idx}
          elevation={0}
          sx={{ 
            p: 2.5, 
            mb: 1.5, 
            borderRadius: "12px", 
            border: "1px solid", 
            borderColor: "rgba(0,0,0,0.06)",
            transition: "all 0.2s",
            "&:hover": {
              borderColor: "primary.main",
              boxShadow: "0 4px 20px -5px rgba(0,0,0,0.05)",
              transform: "translateX(4px)"
            }
          }}
        >
          <Grid container spacing={2} alignItems="center">
            <Grid sx={{ display: "flex", alignItems: "center", minWidth: 40 }}>
              <Box 
                sx={{ 
                  width: 28, 
                  height: 28, 
                  borderRadius: "50%", 
                  bgcolor: "rgba(15, 23, 42, 0.05)", 
                  color: "text.secondary",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "12px",
                  fontWeight: 700
                }}
              >
                {idx + 1}
              </Box>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "text.primary" }}>
                {step.krok.toUpperCase().replace(/^\d+\.\s*/, '')}
              </Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box sx={{ px: 1.5, py: 0.5, bgcolor: "rgba(0,0,0,0.03)", borderRadius: "6px", border: "1px solid rgba(0,0,0,0.05)" }}>
                  <Typography variant="caption" sx={{ fontSize: "12px", color: "text.secondary", fontFamily: "monospace" }}>
                    {step.rownanie || "---"}
                  </Typography>
                </Box>
                {step.rownanie && (
                  <Tooltip title="Formuła obliczeniowa zgodna z V3 Logic Matrix">
                    <Info size={14} color="#94a3b8" />
                  </Tooltip>
                )}
              </Box>
            </Grid>
            <Grid size={{ xs: 12, sm: 2.5 }} sx={{ textAlign: "right" }}>
              <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1, color: "primary.main" }}>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  {step.wynik.toLocaleString('pl-PL', { minimumFractionDigits: 2 })}
                </Typography>
                <Typography variant="caption" sx={{ fontWeight: 600 }}>PLN</Typography>
              </Box>
            </Grid>
            <Grid sx={{ display: "flex", justifyContent: "flex-end", minWidth: 40 }}>
              <CheckCircle2 size={18} color="#10b981" />
            </Grid>
          </Grid>
        </Paper>
      ))}

      <Box sx={{ mt: 4, pt: 3, borderTop: "1px solid rgba(0,0,0,0.06)", display: "flex", justifyContent: "flex-end" }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Info size={14} /> System v3.0 Final Engine | Temperature 0.0 | No Hallucinations Allowed
        </Typography>
      </Box>
    </Box>
  );
}
