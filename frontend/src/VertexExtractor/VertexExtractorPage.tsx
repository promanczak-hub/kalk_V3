import { useVehicles } from "./hooks/useVehicles";
import { useDocumentProcessing } from "./hooks/useDocumentProcessing";
import { UploadZone } from "./components/UploadZone";
import { DocumentList } from "./components/DocumentList";
import { VehicleTable } from "./components/VehicleTable";
import { JsonViewerModal } from "./components/JsonViewerModal";
import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config/env";
import type { ControlCenterSettings } from "../types";
import {
  Box,
  Container,
  Typography,
  Fab,
  Stack,
  useTheme,
  Tooltip,
} from "@mui/material";
import { CreateManualModal } from "../ManualKalkulacje/CreateManualModal";
import { FilePlus } from "lucide-react";
import { motion } from "framer-motion";

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
    globalSearchQuery,
    setGlobalSearchQuery,
    isSearching,
    liveSearchText,
    setLiveSearchText,
    fetchSavedVehicles,
    handleGlobalSearch,
    handleDeleteVehicle,
    page,
    setPage,
    pageSize,
    totalCount,
  } = useVehicles();

  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [globalSettings, setGlobalSettings] = useState<ControlCenterSettings | null>(null);
  const [bodyTypes, setBodyTypes] = useState<any[]>([]);
  const [paintTypes, setPaintTypes] = useState<any[]>([]);

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
        const [{ data: bodies }, { data: paints }] = await Promise.all([
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (window as any).supabase.from("body_types").select("*").order("nazwa_nadwozia"),
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (window as any).supabase.from("paint_types").select("*").order("id")
        ]);
        if (bodies) setBodyTypes(bodies);
        if (paints) setPaintTypes(paints);
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

  return (
    <Box sx={{ pb: 6, minHeight: "100vh" }}>
      <Container maxWidth="xl">
        {/* Hero Section - Compacted */}
        <Stack spacing={2} sx={{ mb: 4 }}>
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <Box sx={{ mt: 1 }}>
              <Typography
                variant="h5"
                component="h1"
                sx={{
                  fontWeight: 800,
                  background: "linear-gradient(45deg, #1e3a8a 30%, #3b82f6 90%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: "-0.02em",
                  mb: 0.5,
                }}
              >
                Ekstrakcja i Analiza AI
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 700, fontSize: '0.85rem' }}>
                Prześlij dokumenty pojazdów (zdjęcia, PDF), aby wyodrębnić dane techniczne i finansowe za pomocą AI.
              </Typography>
            </Box>
          </motion.div>

          {/* Core Workflow - Compact Spacing */}
          <UploadZone onFilesSelected={handleFiles} />
          
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
              globalSearchQuery={globalSearchQuery}
              isSearching={isSearching}
              setGlobalSearchQuery={setGlobalSearchQuery}
              handleGlobalSearch={handleGlobalSearch}
              liveSearchText={liveSearchText}
              setLiveSearchText={setLiveSearchText}
              fetchSavedVehicles={fetchSavedVehicles}
              handleOpenSavedJson={handleOpenSavedJson}
              handleDeleteVehicle={handleDeleteVehicle}
              globalSettings={globalSettings}
              bodyTypes={bodyTypes}
              paintTypes={paintTypes}
              page={page}
              setPage={setPage}
              pageSize={pageSize}
              totalCount={totalCount}
              highlightVehicleId={highlightVehicleId}
            />
          </Box>
        </Stack>
  
        <Tooltip title="Nowa Kalkulacja Manualna" placement="left">
          <Fab
            color="secondary"
            aria-label="nowa kalkulacja manualna"
            onClick={() => setManualModalOpen(true)}
            sx={{
              position: "fixed",
              bottom: 104, // Offset to sit above the Offer Cart FAB (usually at 32)
              right: 32,
              zIndex: 1100,
              background: "linear-gradient(45deg, #4f46e5 30%, #7c3aed 90%)",
              boxShadow: theme.palette.mode === 'dark' 
                ? "0 8px 32px rgba(79, 70, 229, 0.4)" 
                : "0 8px 20px rgba(79, 70, 229, 0.25)",
              "&:hover": {
                transform: "scale(1.08)",
                transition: "transform 0.2s ease-in-out",
              },
            }}
          >
            <FilePlus />
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
    </Box>
  );
}
