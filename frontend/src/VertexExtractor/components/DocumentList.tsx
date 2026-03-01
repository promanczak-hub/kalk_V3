import { UploadCloud } from "lucide-react";
import type { UploadedDocument } from "../types";
import { DocumentCard } from "./ui/DocumentCard";

interface DocumentListProps {
  documents: UploadedDocument[];
  onOpenJson: (doc: UploadedDocument) => void;
  onRemoveDocument: (id: string) => void;
}

export function DocumentList({
  documents,
  onOpenJson,
  onRemoveDocument,
}: DocumentListProps) {
  if (documents.length === 0) return null;

  return (
    <div className="w-full mt-8">
      <h2 className="text-xl font-semibold mb-6 text-slate-800 dark:text-slate-200 px-2 flex items-center gap-2">
        <UploadCloud className="w-5 h-5 text-indigo-500" /> Przetwarzane
        dokumenty
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {documents.map((doc) => (
          <DocumentCard
            key={doc.id}
            doc={doc}
            onOpenJson={() => onOpenJson(doc)}
            onRemove={() => onRemoveDocument(doc.id)}
          />
        ))}
      </div>
    </div>
  );
}
