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
import { Button, Box } from "@mui/material";
import CalculateOutlinedIcon from "@mui/icons-material/CalculateOutlined";
import { CreateManualModal } from "../ManualKalkulacje/CreateManualModal";
import { useNavigate } from "react-router-dom";

export default function VertexExtractorPage() {
  // Read the ?highlight=<uuid> deep-link param on mount, then clean URL
  const highlightVehicleId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("highlight") ?? null;
  }, []);

  useEffect(() => {
    if (highlightVehicleId) {
      // Clean up ?highlight= from URL bar without triggering re-render
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

  const navigate = useNavigate();
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
    <div className="min-h-screen text-slate-900 font-sans selection:bg-orange-100">
      <main className="w-full px-4 py-8 md:py-16 md:px-8">

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
          <Button
            variant="outlined"
            startIcon={<CalculateOutlinedIcon />}
            onClick={() => setManualModalOpen(true)}
            sx={{ textTransform: 'none', fontWeight: 500 }}
          >
            Nowa kalkulacja manualna
          </Button>
        </Box>

        <UploadZone onFilesSelected={handleFiles} />

        <DocumentList
          documents={documents}
          onOpenJson={(doc) => setActiveJsonView(doc)}
          onRemoveDocument={removeDocument}
        />

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
      </main>

      <JsonViewerModal
        activeJsonView={activeJsonView}
        onClose={() => setActiveJsonView(null)}
        onSaveToDatabase={handleSaveToDatabase}
        isSaving={isSaving}
      />

      <CreateManualModal
        open={manualModalOpen}
        onClose={() => setManualModalOpen(false)}
        onCreated={() => {
          setManualModalOpen(false);
          navigate('/kalkulacje');
        }}
      />
    </div>
  );
}

