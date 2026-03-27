import { Box, Typography, Grid } from "@mui/material";
import FileUploadOutlinedIcon from "@mui/icons-material/FileUploadOutlined";
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
    <Box sx={{ w: "100%", mt: 6 }}>
      <Box sx={{ mb: 3, px: 1, display: "flex", alignItems: "center", gap: 1.5 }}>
        <FileUploadOutlinedIcon color="primary" sx={{ fontSize: "1.5rem" }} />
        <Typography variant="h6" sx={{ fontWeight: 700 }}>
          Przetwarzane dokumenty
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {documents.map((doc) => (
          <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={doc.id}>
            <DocumentCard
              doc={doc}
              onOpenJson={() => onOpenJson(doc)}
              onRemove={() => onRemoveDocument(doc.id)}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
