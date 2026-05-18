import { Box, Chip, Stack, Typography } from "@mui/material";
import type { ZabudowaSotKey } from "./types";
import { ZABUDOWA_LABEL, ZABUDOWA_PALETTE_ORDER } from "./types";

interface ZabudowaPaletteProps {
  selected: ZabudowaSotKey | null;
  onSelect: (key: ZabudowaSotKey | null) => void;
}

export function ZabudowaPalette({ selected, onSelect }: ZabudowaPaletteProps) {
  return (
    <Box
      sx={{
        mb: 1.5,
        p: 1.25,
        borderRadius: 1.5,
        bgcolor: "primary.50",
        border: "1px solid",
        borderColor: "primary.light",
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        Typ zabudowy (SOT body_types):
      </Typography>
      <Stack direction="row" spacing={0.75} mt={0.5} flexWrap="wrap" useFlexGap>
        {ZABUDOWA_PALETTE_ORDER.map((key) => (
          <Chip
            key={key}
            label={ZABUDOWA_LABEL[key]}
            onClick={() => onSelect(selected === key ? null : key)}
            color={selected === key ? "primary" : "default"}
            variant={selected === key ? "filled" : "outlined"}
            size="small"
            clickable
          />
        ))}
      </Stack>
    </Box>
  );
}
