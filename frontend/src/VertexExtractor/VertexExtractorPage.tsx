import { useVehicles } from "./hooks/useVehicles";
import { useDocumentProcessing } from "./hooks/useDocumentProcessing";

import { UploadZone } from "./components/UploadZone";
import { DocumentList } from "./components/DocumentList";
import { VehicleTable } from "./components/VehicleTable";
import { JsonViewerModal } from "./components/JsonViewerModal";

export default function VertexExtractorPage() {
  const {
    savedVehicles,
    isLoadingSaved,
    globalSearchQuery,
    setGlobalSearchQuery,
    isSearching,
    fetchSavedVehicles,
    handleGlobalSearch,
    handleDeleteVehicle,
  } = useVehicles();

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
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-orange-100">
      <main className="w-full px-4 py-8 md:py-16 md:px-8">

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
          fetchSavedVehicles={fetchSavedVehicles}
          handleOpenSavedJson={handleOpenSavedJson}
          handleDeleteVehicle={handleDeleteVehicle}
        />
      </main>

      <JsonViewerModal
        activeJsonView={activeJsonView}
        onClose={() => setActiveJsonView(null)}
        onSaveToDatabase={handleSaveToDatabase}
        isSaving={isSaving}
      />
    </div>
  );
}
