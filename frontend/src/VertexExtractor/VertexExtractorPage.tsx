import { useVehicles } from "./hooks/useVehicles";
import { useDocumentProcessing } from "./hooks/useDocumentProcessing";
import { useHITLWizard } from "./hooks/useHITLWizard";
import { DocumentList } from "./components/DocumentList";
import { VehicleTable } from "./components/VehicleTable";
import { JsonViewerModal } from "./components/JsonViewerModal";
import { HITLWizardDialog } from "./components/HITLWizard/HITLWizardDialog";
import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config/env";
import type { ControlCenterSettings } from "../types";
import { supabase } from "../lib/supabaseClient";
import {
  Box,
  Container,
  Fab,
  Stack,
  useTheme,
  Tooltip,
} from "@mui/material";
import { CreateManualModal } from "../ManualKalkulacje/CreateManualModal";
import { UploadCloud } from "lucide-react";

interface BodyTypeOption {
  id: number;
  name: string;
  vehicle_class: string;
}

interface PaintTypeOption {
  id: number;
  name: string;
  [key: string]: unknown;
}

export default function VertexExtractorPage() {
  const theme = useTheme();
  const highlightVehicleId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("highlight") ?? null;
  }, []);

  useEffect(() => {
    if (highlightVehicleId) {
      const cleanUrl = window.location.pathname;
      window.history.replaceState(null, "", cleanUrl);
    }
  }, [highlightVehicleId]);

  const {
    savedVehicles,
    isLoadingSaved,
    liveSearchText,
    setLiveSearchText,
    fetchSavedVehicles,
    handleDeleteVehicle,
    page,
    setPage,
    pageSize,
    totalCount,
  } = useVehicles();

  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [globalSettings, setGlobalSettings] = useState<ControlCenterSettings | null>(null);
  const [bodyTypes, setBodyTypes] = useState<BodyTypeOption[]>([]);
  const [paintTypes, setPaintTypes] = useState<PaintTypeOption[]>([]);
  const [driveTypes, setDriveTypes] = useState<string[]>([]);
  const [transmissionTypes, setTransmissionTypes] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };


  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const resp = await axios.get<ControlCenterSettings>(
          `${API_BASE_URL}/api/control-center`,
        );
        if (resp.data) {
          setGlobalSettings(resp.data);
        }
      } catch (e) {
        console.error("Failed to fetch settings", e);
      }
    };

    const fetchLookupData = async () => {
      try {
        const [{ data: bodies }, { data: paints }, { data: drives }, { data: transmissions }] = await Promise.all([
          supabase.from("body_types").select("*").order("nazwa_nadwozia"),
          supabase.from("paint_types").select("*").order("id"),
          supabase.from("samar_service_drive_multipliers").select("drive_normalized"),
          supabase.from("transmission_types").select("name").order("id")
        ]);
        if (bodies) {
          // Normalizacja pól bazy (nazwa_nadwozia, typ_pojazdu) → kształt oczekiwany przez BodyTypeTag (name, vehicle_class)
          setBodyTypes(bodies.map((item: { id: number; nazwa_nadwozia?: string; name?: string; typ_pojazdu?: string; vehicle_class?: string }) => ({
            id: item.id,
            name: item.nazwa_nadwozia || item.name || "",
            vehicle_class: item.typ_pojazdu || item.vehicle_class || "",
          })));
        }
        if (paints) setPaintTypes(paints);
        
        if (drives) {
          const validDrives = Array.from(new Set(drives.map(d => d.drive_normalized).filter(Boolean)));
          setDriveTypes(validDrives);
        }
        if (transmissions) {
          setTransmissionTypes(transmissions.map((t: { name: string }) => t.name).filter(Boolean));
        }
      } catch (e) {
        console.error("Failed to fetch lookup data", e);
      }
    };

    fetchSettings();
    fetchLookupData();
  }, []);
  const {
    documents,
    activeJsonView,
    setActiveJsonView,
    isSaving,
    handleFiles,
    handleSaveToDatabase,
    handleOpenSavedJson,
    removeDocument,
  } = useDocumentProcessing(fetchSavedVehicles);

  const hitl = useHITLWizard();

  return (
    <Box sx={{ pb: 6, minHeight: "100vh" }}>
      <Container maxWidth="xl">
        {/* Main Content Area */}
        <Stack spacing={2} sx={{ mb: 4, mt: 2 }}>
          {documents.length > 0 && (
            <DocumentList
              documents={documents}
              onOpenJson={(doc) => setActiveJsonView(doc)}
              onRemoveDocument={removeDocument}
            />
          )}

          <Box sx={{ mt: 2 }}>
            <VehicleTable
              savedVehicles={savedVehicles}
              isLoadingSaved={isLoadingSaved}

              liveSearchText={liveSearchText}
              setLiveSearchText={setLiveSearchText}
              fetchSavedVehicles={fetchSavedVehicles}
              handleOpenSavedJson={handleOpenSavedJson}
              handleDeleteVehicle={handleDeleteVehicle}
              globalSettings={globalSettings}
              bodyTypes={bodyTypes}
              paintTypes={paintTypes}
              driveTypes={driveTypes}
              transmissionTypes={transmissionTypes}
              page={page}
              setPage={setPage}
              pageSize={pageSize}
              totalCount={totalCount}
              highlightVehicleId={highlightVehicleId}
              onOpenHITL={(v) =>
                hitl.openForVehicle({
                  id: v.id,
                  brand: v.brand ?? undefined,
                  model: v.model ?? undefined,
                  verification_status: v.verification_status ?? undefined,
                  synthesis_data: v.synthesis_data as Record<string, unknown>,
                })
              }
            />
          </Box>
        </Stack>
  
        <Tooltip title="Rozpocznij AI Ekstrakcję" placement="left">
          <Fab
            component="label"
            aria-label="prześlij dokumenty"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            sx={{
              position: "fixed",
              bottom: 104, // Offset to sit above the Offer Cart FAB (usually at 32)
              right: 32,
              zIndex: 1100,
              background: isDragging 
                ? "linear-gradient(45deg, #6366f1 30%, #a855f7 90%)"
                : "linear-gradient(45deg, #4f46e5 30%, #7c3aed 90%)",
              color: "#ffffff",
              boxShadow: isDragging
                ? "0 12px 48px rgba(79, 70, 229, 0.6)"
                : (theme.palette.mode === 'dark' 
                  ? "0 8px 32px rgba(79, 70, 229, 0.4)" 
                  : "0 8px 20px rgba(79, 70, 229, 0.25)"),
              transform: isDragging ? "scale(1.15)" : "scale(1)",
              transition: "all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
              "&:hover": {
                transform: "scale(1.08)",
              },
            }}
          >
            <UploadCloud />
            <input
              type="file"
              hidden
              multiple
              accept=".pdf,.xls,.xlsx,.png,.jpg,.jpeg"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFiles(Array.from(e.target.files));
                }
              }}
            />
          </Fab>
        </Tooltip>
      </Container>

      {/* Manual Calculation Modals */}
      <CreateManualModal
        open={manualModalOpen}
        onClose={() => setManualModalOpen(false)}
        onCreated={() => {
          setManualModalOpen(false);
          fetchSavedVehicles();
        }}
      />

      <JsonViewerModal
        activeJsonView={activeJsonView}
        onClose={() => setActiveJsonView(null)}
        onSaveToDatabase={handleSaveToDatabase}
        isSaving={isSaving}
      />

      <HITLWizardDialog
        controller={hitl}
        onSaved={() => fetchSavedVehicles()}
      />
    </Box>
  );
}
