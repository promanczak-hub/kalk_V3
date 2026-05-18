import { useDroppable } from "@dnd-kit/core";
import { Box, Chip, Stack, Typography } from "@mui/material";
import type { BucketId, ItemDraft, PriceType } from "./types";
import { BUCKET_LABEL } from "./types";
import { ItemCard } from "./ItemCard";

interface BucketZoneProps {
  bucketId: BucketId;
  items: ItemDraft[];
  totalGross: number;
  onPriceChange: (field_id: string, value: number) => void;
  onPriceTypeChange: (field_id: string, type: PriceType) => void;
  onVatRateChange: (field_id: string, rate: number) => void;
  emphasize?: boolean; // np. dla bucket-u zabudowa gdy palette też jest widoczna
  children?: React.ReactNode; // np. ZabudowaPalette wewnątrz
}

export function BucketZone({
  bucketId,
  items,
  totalGross,
  onPriceChange,
  onPriceTypeChange,
  onVatRateChange,
  emphasize,
  children,
}: BucketZoneProps) {
  const { setNodeRef, isOver } = useDroppable({ id: bucketId });

  return (
    <Box
      ref={setNodeRef}
      sx={{
        p: 1.5,
        borderRadius: 2,
        border: "2px dashed",
        borderColor: isOver ? "primary.main" : emphasize ? "primary.light" : "divider",
        bgcolor: isOver ? "primary.50" : "background.default",
        minHeight: 80,
        transition: "all .15s",
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
          {BUCKET_LABEL[bucketId]}
        </Typography>
        {items.length > 0 && (
          <Chip
            size="small"
            label={`${items.length}× • ${totalGross.toLocaleString("pl-PL", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })} zł brutto`}
            color={bucketId === "skip" ? "default" : "primary"}
            variant="outlined"
            sx={{ fontFamily: "monospace", fontSize: 11 }}
          />
        )}
      </Stack>
      {children}
      <Stack spacing={1}>
        {items.map((item) => (
          <ItemCard
            key={item.field_id}
            item={item}
            isInBucket
            onPriceChange={onPriceChange}
            onPriceTypeChange={onPriceTypeChange}
            onVatRateChange={onVatRateChange}
          />
        ))}
        {items.length === 0 && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontStyle: "italic", px: 1 }}
          >
            Przeciągnij tutaj pozycje z lewej kolumny
          </Typography>
        )}
      </Stack>
    </Box>
  );
}
