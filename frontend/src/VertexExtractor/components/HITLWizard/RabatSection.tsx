import {
  Box,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormGroup,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { Tag } from "lucide-react";
import type { DiscountDraft, RabatBasis, RabatType } from "./types";

interface RabatSectionProps {
  discount: DiscountDraft;
  onChange: (next: DiscountDraft) => void;
  bucketTotals: {
    base: number;
    factory: number;
    zabudowa: number;
    agregat: number;
  };
}

const SCOPE_OPTIONS: {
  key: "base" | "factory_options" | "zabudowa" | "agregat";
  label: string;
}[] = [
  { key: "base", label: "Cena bazowa pojazdu" },
  { key: "factory_options", label: "Opcje fabryczne" },
  { key: "zabudowa", label: "Zabudowa" },
  { key: "agregat", label: "Agregat / wyposażenie dodatkowe" },
];

function computeBase(
  scope: ("base" | "factory_options" | "zabudowa" | "agregat")[],
  totals: RabatSectionProps["bucketTotals"]
): number {
  let sum = 0;
  if (scope.includes("base")) sum += totals.base;
  if (scope.includes("factory_options")) sum += totals.factory;
  if (scope.includes("zabudowa")) sum += totals.zabudowa;
  if (scope.includes("agregat")) sum += totals.agregat;
  return sum;
}

function fmtPln(n: number): string {
  return n.toLocaleString("pl-PL", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function RabatSection({ discount, onChange, bucketTotals }: RabatSectionProps) {
  const discountableBase = computeBase(discount.discount_scope, bucketTotals);

  const effectivePct =
    discount.rabat_type === "kwotowo"
      ? discountableBase > 0
        ? (discount.rabat_value / discountableBase) * 100
        : 0
      : discount.rabat_value;

  const effectiveAmount =
    discount.rabat_type === "kwotowo"
      ? discount.rabat_value
      : (discount.rabat_value / 100) * discountableBase;

  const afterDiscount = Math.max(0, discountableBase - effectiveAmount);

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
      <Stack direction="row" alignItems="center" spacing={1} mb={1.5}>
        <Tag size={18} />
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          Rabat
        </Typography>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <Stack spacing={1.25} flex={1}>
          <FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
              Typ rabatu
            </Typography>
            <ToggleButtonGroup
              size="small"
              value={discount.rabat_type}
              exclusive
              onChange={(_, v) =>
                v && onChange({ ...discount, rabat_type: v as RabatType })
              }
            >
              <ToggleButton value="kwotowo">Kwotowo (PLN)</ToggleButton>
              <ToggleButton value="procentowo">Procentowo (%)</ToggleButton>
            </ToggleButtonGroup>
          </FormControl>

          <FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
              Wartość rabatu
            </Typography>
            <TextField
              size="small"
              type="number"
              value={discount.rabat_value}
              onChange={(e) =>
                onChange({
                  ...discount,
                  rabat_value: parseFloat(e.target.value) || 0,
                })
              }
              inputProps={{ step: "0.01" }}
            />
          </FormControl>

          <FormControl>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
              Baza
            </Typography>
            <ToggleButtonGroup
              size="small"
              value={discount.rabat_basis}
              exclusive
              onChange={(_, v) =>
                v && onChange({ ...discount, rabat_basis: v as RabatBasis })
              }
            >
              <ToggleButton value="netto">Netto</ToggleButton>
              <ToggleButton value="brutto">Brutto</ToggleButton>
            </ToggleButtonGroup>
          </FormControl>
        </Stack>

        <Stack spacing={1} flex={1.5}>
          <Typography variant="caption" color="text.secondary">
            Rabat dotyczy:
          </Typography>
          <FormGroup>
            {SCOPE_OPTIONS.map((opt) => {
              const checked = discount.discount_scope.includes(opt.key);
              return (
                <FormControlLabel
                  key={opt.key}
                  control={
                    <Checkbox
                      checked={checked}
                      size="small"
                      onChange={(e) => {
                        const next = e.target.checked
                          ? [...discount.discount_scope, opt.key]
                          : discount.discount_scope.filter((s) => s !== opt.key);
                        onChange({ ...discount, discount_scope: next });
                      }}
                    />
                  }
                  label={
                    <Typography variant="body2">
                      {opt.label}{" "}
                      <Typography
                        component="span"
                        variant="caption"
                        color="text.secondary"
                      >
                        ({fmtPln(bucketTotals[opt.key === "factory_options" ? "factory" : opt.key])} zł)
                      </Typography>
                    </Typography>
                  }
                />
              );
            })}
          </FormGroup>
        </Stack>
      </Stack>

      <Box mt={2} p={1.5} bgcolor="grey.50" borderRadius={1}>
        <Stack spacing={0.5}>
          <Typography variant="body2">
            <strong>Cena bazowa do rabatu:</strong>{" "}
            <span style={{ fontFamily: "monospace" }}>{fmtPln(discountableBase)} zł brutto</span>
          </Typography>
          <Typography variant="body2">
            <strong>Rabat efektywny:</strong>{" "}
            <span style={{ fontFamily: "monospace" }}>
              {effectivePct.toFixed(2)}% ({fmtPln(effectiveAmount)} zł)
            </span>
          </Typography>
          <Typography variant="body2">
            <strong>Po rabacie:</strong>{" "}
            <span style={{ fontFamily: "monospace" }}>{fmtPln(afterDiscount)} zł brutto</span>
          </Typography>
        </Stack>
      </Box>
    </Paper>
  );
}
