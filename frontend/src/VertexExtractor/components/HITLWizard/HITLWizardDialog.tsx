import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";
import { X } from "lucide-react";
import { useHITLWizard } from "../../hooks/useHITLWizard";
import { BucketZone } from "./BucketZone";
import { ItemCard } from "./ItemCard";
import { LivePreviewPanel } from "./LivePreviewPanel";
import { RabatSection } from "./RabatSection";
import { ZabudowaPalette } from "./ZabudowaPalette";
import {
  BUCKET_ORDER,
  CABIN_LABEL,
  CABIN_PALETTE_ORDER,
  type BucketId,
  type CabinKind,
} from "./types";

interface HITLWizardDialogProps {
  controller: ReturnType<typeof useHITLWizard>;
  onSaved?: (vehicleId: string) => void;
}

export function HITLWizardDialog({ controller, onSaved }: HITLWizardDialogProps) {
  const {
    isOpen,
    vehicle,
    items,
    cabinKind,
    setCabinKind,
    zabudowaSotKey,
    setZabudowaSotKey,
    discount,
    setDiscount,
    preview,
    previewLoading,
    previewError,
    isSaving,
    bucketTotals,
    close,
    moveItem,
    updatePrice,
    updatePriceType,
    updateVatRate,
    save,
  } = controller;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  );

  const unassigned = items.filter((it) => !BUCKET_ORDER.includes(it.bucket as BucketId));
  const byBucket: Record<BucketId, typeof items> = {
    base: items.filter((it) => it.bucket === "base"),
    factory: items.filter((it) => it.bucket === "factory"),
    zabudowa: items.filter((it) => it.bucket === "zabudowa"),
    agregat: items.filter((it) => it.bucket === "agregat"),
    skip: items.filter((it) => it.bucket === "skip"),
  };

  const handleDragEnd = (e: DragEndEvent) => {
    const overId = e.over?.id;
    if (!overId || typeof overId !== "string") return;
    if (!BUCKET_ORDER.includes(overId as BucketId)) return;
    moveItem(String(e.active.id), overId as BucketId);
  };

  const handleSave = async () => {
    const res = await save();
    if (res && vehicle && onSaved) onSaved(vehicle.id);
  };

  if (!vehicle) return null;
  const brandModel = `${vehicle.brand ?? ""} ${vehicle.model ?? ""}`.trim();

  return (
    <Dialog
      open={isOpen}
      onClose={close}
      fullWidth
      maxWidth="lg"
      PaperProps={{ sx: { borderRadius: 3 } }}
      data-testid="hitl-wizard-dialog"
    >
      <DialogTitle sx={{ pr: 6 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              Sprawdź dane wyekstrahowane
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {brandModel || vehicle.id}
            </Typography>
          </Box>
          <IconButton onClick={close} aria-label="zamknij">
            <X size={20} />
          </IconButton>
        </Stack>

        <Stack direction="row" spacing={2} mt={1.5} alignItems="center" flexWrap="wrap">
          <Box>
            <Typography variant="caption" color="text.secondary">
              Cabin / Kabina
            </Typography>
            <Select
              size="small"
              value={cabinKind ?? ""}
              onChange={(e) => setCabinKind((e.target.value as CabinKind) || null)}
              displayEmpty
              sx={{ minWidth: 200, ml: 1 }}
            >
              <MenuItem value="">(wybierz)</MenuItem>
              {CABIN_PALETTE_ORDER.map((k) => (
                <MenuItem key={k} value={k}>
                  {CABIN_LABEL[k]}
                </MenuItem>
              ))}
            </Select>
          </Box>
        </Stack>
      </DialogTitle>

      <DialogContent dividers>
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            {/* Lewa kolumna: lista pozycji (już rozdzielone do bucketów, pozostałe = unassigned) */}
            <Box flex={1} minWidth={0}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Pozycje do przypisania (sortowane od najmniej pewnych)
              </Typography>
              <Stack spacing={1}>
                {/* If any item is unassigned (shouldn't usually happen since default = factory) */}
                {unassigned.map((it) => (
                  <ItemCard
                    key={it.field_id}
                    item={it}
                    isInBucket={false}
                    onPriceChange={updatePrice}
                    onPriceTypeChange={updatePriceType}
                    onVatRateChange={updateVatRate}
                  />
                ))}
                {items.length === 0 && (
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                    Brak pozycji wymagających review — możesz zamknąć wizard.
                  </Typography>
                )}
                {vehicle.synthesis_data?.card_summary?.hallucinated_fields &&
                  vehicle.synthesis_data.card_summary.hallucinated_fields.length > 0 && (
                    <Alert severity="warning" data-testid="hallucinations-alert">
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                        🚨 LLM wykrył halucynacje
                      </Typography>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        {vehicle.synthesis_data.card_summary.hallucinated_fields.map((h) => (
                          <Chip key={h} label={h} size="small" color="warning" />
                        ))}
                      </Stack>
                    </Alert>
                  )}
              </Stack>
            </Box>

            {/* Prawa kolumna: bucket-y */}
            <Box flex={1.2} minWidth={0}>
              <Stack spacing={1.5}>
                <BucketZone
                  bucketId="base"
                  items={byBucket.base}
                  totalGross={bucketTotals.base}
                  onPriceChange={updatePrice}
                  onPriceTypeChange={updatePriceType}
                  onVatRateChange={updateVatRate}
                />
                <BucketZone
                  bucketId="factory"
                  items={byBucket.factory}
                  totalGross={bucketTotals.factory}
                  onPriceChange={updatePrice}
                  onPriceTypeChange={updatePriceType}
                  onVatRateChange={updateVatRate}
                />
                <BucketZone
                  bucketId="zabudowa"
                  items={byBucket.zabudowa}
                  totalGross={bucketTotals.zabudowa}
                  emphasize={byBucket.zabudowa.length > 0}
                  onPriceChange={updatePrice}
                  onPriceTypeChange={updatePriceType}
                  onVatRateChange={updateVatRate}
                >
                  {(byBucket.zabudowa.length > 0 || zabudowaSotKey) && (
                    <ZabudowaPalette
                      selected={zabudowaSotKey}
                      onSelect={setZabudowaSotKey}
                    />
                  )}
                </BucketZone>
                <BucketZone
                  bucketId="agregat"
                  items={byBucket.agregat}
                  totalGross={bucketTotals.agregat}
                  onPriceChange={updatePrice}
                  onPriceTypeChange={updatePriceType}
                  onVatRateChange={updateVatRate}
                />
                <BucketZone
                  bucketId="skip"
                  items={byBucket.skip}
                  totalGross={0}
                  onPriceChange={updatePrice}
                  onPriceTypeChange={updatePriceType}
                  onVatRateChange={updateVatRate}
                />
              </Stack>
            </Box>
          </Stack>

          <Divider sx={{ my: 2 }} />

          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Box flex={1}>
              <RabatSection
                discount={discount}
                onChange={setDiscount}
                bucketTotals={bucketTotals}
              />
            </Box>
            <Box flex={1}>
              <LivePreviewPanel
                loading={previewLoading}
                data={preview}
                validationError={previewError}
              />
            </Box>
          </Stack>
        </DndContext>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={close} color="inherit">
          Pomiń wizard
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={isSaving}
          data-testid="hitl-save-button"
        >
          {isSaving ? "Zapisuję..." : "Zapisz korekty"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
