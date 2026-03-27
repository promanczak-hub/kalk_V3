import { useVehicles } from "./hooks/useVehicles";
import { useDocumentProcessing } from "./hooks/useDocumentProcessing";
import { UploadZone } from "./components/UploadZone";
import { DocumentList } from "./components/DocumentList";
import { VehicleTable } from "./components/VehicleTable";
import { JsonViewerModal } from "./components/JsonViewerModal";
import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config/env";
import type { ControlCenterSettings } from "../hooks/useCalculator";
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
    fetchSettings();
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
    <Box sx={{ pb: 8, minHeight: "100vh" }}>
      <Container maxWidth="xl">
        {/* Hero Section */}
        <Stack spacing={4} sx={{ mb: 6 }}>
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Box>
              <Typography
                variant="h4"
                component="h1"
                gutterBottom
                sx={{
                  fontWeight: 800,
                  background: "linear-gradient(45deg, #1e3a8a 30%, #3b82f6 90%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: "-0.02em",
                }}
              >
                Ekstrakcja i Analiza AI
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600 }}>
                Prześlij dokumenty pojazdów (zdjęcia, PDF), aby automatycznie wyodrębnić dane techniczne i finansowe za pomocą sztucznej inteligencji.
              </Typography>
            </Box>
          </motion.div>

          {/* Core Workflow */}
          <UploadZone onFilesSelected={handleFiles} />
          
          <DocumentList
            documents={documents}
            onOpenJson={(doc) => setActiveJsonView(doc)}
            onRemoveDocument={removeDocument}
          />

          <Box sx={{ mt: 4 }}>
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
