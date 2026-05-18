import { useDraggable } from "@dnd-kit/core";
import { Box, Chip, MenuItem, Select, Stack, TextField, ToggleButton, ToggleButtonGroup, Tooltip, Typography } from "@mui/material";
import { AlertTriangle } from "lucide-react";
import type { ItemDraft, PriceType } from "./types";
import { confidenceColor } from "./types";

interface ItemCardProps {
  item: ItemDraft;
  isInBucket: boolean;
  onPriceChange: (field_id: string, value: number) => void;
  onPriceTypeChange: (field_id: string, type: PriceType) => void;
  onVatRateChange: (field_id: string, rate: number) => void;
}

const DOT_BG: Record<"red" | "amber" | "green", string> = {
  red: "#ef4444",
  amber: "#f59e0b",
  green: "#10b981",
};

export function ItemCard({
  item,
  isInBucket,
  onPriceChange,
  onPriceTypeChange,
  onVatRateChange,
}: ItemCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.field_id,
  });

  const color = confidenceColor(item.confidence);
  const style: React.CSSProperties = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: 1000,
      }
    : {};

  return (
    <Box
      ref={setNodeRef}
      style={style}
      sx={{
        p: 1.25,
        borderRadius: 2,
        border: "1px solid",
        borderColor: isInBucket ? "primary.light" : "divider",
        bgcolor: isInBucket ? "primary.50" : "background.paper",
        opacity: isDragging ? 0.4 : 1,
        cursor: "grab",
        touchAction: "none",
        "&:hover": { borderColor: "primary.main" },
      }}
    >
      <Stack spacing={0.75}>
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          {...listeners}
          {...attributes}
        >
          <Box
            sx={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              bgcolor: DOT_BG[color],
              flexShrink: 0,
            }}
            aria-label={`confidence ${item.confidence.toFixed(2)}`}
          />
          <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
            {item.name}
          </Typography>
          {item.is_duplicate_candidate && (
            <Tooltip title="Możliwy duplikat — sprawdź czy ta sama pozycja nie jest w innej sekcji PDF">
              <Chip
                size="small"
                icon={<AlertTriangle size={14} />}
                label="duplikat?"
                color="warning"
                sx={{ height: 22 }}
              />
            </Tooltip>
          )}
        </Stack>

        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            size="small"
            type="number"
            value={item.price_value}
            onChange={(e) => onPriceChange(item.field_id, parseFloat(e.target.value) || 0)}
            inputProps={{ step: "0.01" }}
            sx={{ width: 120 }}
          />
          <Typography variant="caption" color="text.secondary">
            PLN
          </Typography>
          <ToggleButtonGroup
            size="small"
            value={item.price_type}
            exclusive
            onChange={(_, v) => v && onPriceTypeChange(item.field_id, v as PriceType)}
          >
            <ToggleButton value="netto" sx={{ py: 0, px: 1.5, fontSize: 11 }}>
              netto
            </ToggleButton>
            <ToggleButton value="brutto" sx={{ py: 0, px: 1.5, fontSize: 11 }}>
              brutto
            </ToggleButton>
          </ToggleButtonGroup>
          <Select
            size="small"
            value={item.vat_rate}
            onChange={(e) => onVatRateChange(item.field_id, Number(e.target.value))}
            sx={{ minWidth: 70, fontSize: 12, ".MuiSelect-select": { py: 0.5 } }}
          >
            <MenuItem value={0.23}>23%</MenuItem>
            <MenuItem value={0.08}>8%</MenuItem>
            <MenuItem value={0.05}>5%</MenuItem>
            <MenuItem value={0}>0%</MenuItem>
          </Select>
        </Stack>

        <Stack direction="row" spacing={1} alignItems="center">
          {item.source_section && (
            <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
              z {item.source_section}
            </Typography>
          )}
          <Typography variant="caption" sx={{ color: DOT_BG[color], fontFamily: "monospace" }}>
            conf {item.confidence.toFixed(2)}
          </Typography>
        </Stack>
      </Stack>
    </Box>
  );
}
