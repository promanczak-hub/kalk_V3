import { useState, useCallback } from "react";
import { supabase } from "../lib/supabaseClient";
import { v4 as uuidv4 } from "uuid";
import SparkMD5 from "spark-md5";
import type { UploadedDocument } from "../types";

const sanitizeFileName = (name: string): string => {
  const polishMap: Record<string, string> = {
    ą: "a",
    ć: "c",
    ę: "e",
    ł: "l",
    ń: "n",
    ó: "o",
    ś: "s",
    ź: "z",
    ż: "z",
    Ą: "A",
    Ć: "C",
    Ę: "E",
    Ł: "L",
    Ń: "N",
    Ó: "O",
    Ś: "S",
    Ź: "Z",
    Ż: "Z",
  };
  return name
    .replace(/[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/g, (ch) => polishMap[ch] || ch)
    .replace(/\s+/g, "_")
    .replace(/[^a-zA-Z0-9._-]/g, "");
};

export function useDocumentProcessing(onSuccessSaved?: () => void) {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [activeJsonView, setActiveJsonView] = useState<UploadedDocument | null>(
    null,
  );
  const [isSaving, setIsSaving] = useState(false);

  const processDocument = useCallback(
    async (doc: UploadedDocument, fileObj: File) => {
      setDocuments((docs) =>
        docs.map((d) =>
          d.id === doc.id
            ? { ...d, status: "uploading", originalFile: fileObj }
            : d,
        ),
      );

      let md5Hash = "";
      try {
        // 1. Oblicz Hash MD5 pliku
        md5Hash = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            if (e.target?.result) {
              const spark = new SparkMD5.ArrayBuffer();
              spark.append(e.target.result as ArrayBuffer);
              resolve(spark.end());
            } else reject("Błąd odczytu pliku");
          };
          reader.onerror = () => reject(reader.error);
          reader.readAsArrayBuffer(fileObj);
        });

        // 2. Sprawdź duplikat w Supabase na podstawie sumy kontrolnej MD5,
        // ale zignoruj wiersze, które mają status błędu lub zostały anulowane.
        // Oraz na wszelki wypadek zabezpiecz przed wyrzucaniem alertu "null null" dla świeżych "processing", które właśnie dodaliśmy ułamek sekundy temu
        const { data: duplicateRows } = await supabase
          .from("vehicle_synthesis")
          .select("brand, model, verification_status")
          .eq("file_hash", md5Hash)
          .not("verification_status", "in", '("error","cancelled")')
          .limit(1);

        const duplicateData = duplicateRows && duplicateRows.length > 0 ? duplicateRows[0] : null;

        // Tylko jeśli to nie jest nasz nowo utworzony pusty wiersz bez brandu i modelu. 
        // Zapobiega wyświetlaniu alertu "Odrzucono duplikat: Plik X to identyczny dokument co zapisany null null"
        if (duplicateData && (duplicateData.brand || duplicateData.model || duplicateData.verification_status === "completed")) {
          setDocuments((docs) =>
            docs.map((d) =>
              d.id === doc.id
                ? {
                    ...d,
                    status: "error",
                    jsonResult: JSON.stringify(
                      {
                        error: `DUPLIKAT! Ten plik zidentyfikowano już w bazie jako: ${duplicateData.brand || "Nieznana marka"} ${duplicateData.model || ""}`,
                      },
                      null,
                      2,
                    ),
                  }
                : d,
            ),
          );
          alert(
            `Odrzucono duplikat: Plik ${fileObj.name} to identyczny dokument co zapisany ${duplicateData.brand || "Nieznana marka"} ${duplicateData.model || ""}.`,
          );
          return;
        }

        const fileId = uuidv4();
        // Zarezerwuj wiersz w bazie danych by od razu pokazać procesowanie 
        // a asynchroniczny backend zaktualizuje go sam po skończeniu.
        const { error: dbError } = await supabase
          .from("vehicle_synthesis")
          .insert({
            id: fileId,
            verification_status: "processing",
            file_hash: md5Hash,
          });

        if (dbError) {
          throw new Error("Błąd podczas rezerwacji wiersza w bazie: " + dbError.message);
        }

        const formData = new FormData();
        formData.append("file", fileObj);
        formData.append("file_id", fileId);

        setDocuments((docs) =>
          docs.map((d) =>
            d.id === doc.id ? { ...d, status: "processing" } : d,
          ),
        );

        const response = await fetch("http://127.0.0.1:8000/api/extract/async", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errMsg = await response.text();
          throw new Error(
            `Server returned ${response.status} ${response.statusText}: ${errMsg}`,
          );
        }

        // Backend w tle przetwarza plik. 
        // Usuwamy go tymczasowo z kolejki wgranych plików (będzie wisiał na tabeli Kalkulacje z bazy)
        setDocuments((currentDocs) =>
          currentDocs.filter((d) => d.id !== doc.id),
        );

        if (onSuccessSaved) {
          onSuccessSaved();
        }

      } catch (error) {
        console.error("Extraction error:", error);
        
        // Zabezpieczenie: jeśli dostaliśmy ID na początku, oznaczmy ten wpis jako błąd w bazie by nie "wisiał"
        if (md5Hash) {
            try {
                await supabase.from("vehicle_synthesis")
                  .update({ verification_status: "error", notes: String(error) })
                  .eq("file_hash", md5Hash) // uzywamy sumy kontrolnej do odnalezienia zablokowanych encji
                  .or(`verification_status.eq.processing,verification_status.eq.uploading`); // aktualizujemy tylko te co utknęły
            } catch (dbErr) {
                console.error("Failed to fallback update DB on extraction error:", dbErr);
            }
        }

        setDocuments((docs) =>
          docs.map((d) =>
            d.id === doc.id
              ? {
                  ...d,
                  status: "error",
                  jsonResult: JSON.stringify({ error: String(error) }, null, 2),
                }
              : d,
          ),
        );
      }
    },
    [onSuccessSaved],
  );

  const handleFiles = useCallback(
    (files: File[]) => {
      const newDocs = files.map((file) => {
        const isExcel =
          file.name.endsWith(".xls") || file.name.endsWith(".xlsx");
        return {
          id: Math.random().toString(36).substring(7),
          name: file.name,
          size: file.size,
          type: isExcel ? "excel" : "pdf",
          status: "idle",
        } as UploadedDocument;
      });

      setDocuments((prev) => [...newDocs, ...prev]);

      newDocs.forEach((doc, index) => {
        processDocument(doc, files[index]);
      });
    },
    [processDocument],
  );

  const handleSaveToDatabase = useCallback(async () => {
    if (
      !activeJsonView ||
      !activeJsonView.originalFile ||
      !activeJsonView.jsonResult
    )
      return;

    setIsSaving(true);
    try {
      const fileId = uuidv4();
      const fileName = `${fileId}-${sanitizeFileName(activeJsonView.originalFile.name)}`;

      // 1. Upload file to Supabase Storage
      const { error: uploadError } = await supabase.storage
        .from("raw-vehicle-pdfs")
        .upload(fileName, activeJsonView.originalFile);

      if (uploadError)
        throw new Error("File upload failed: " + uploadError.message);

      const { data: publicUrlData } = supabase.storage
        .from("raw-vehicle-pdfs")
        .getPublicUrl(fileName);
      const pdfUrl = publicUrlData.publicUrl;

      // 2. Parse JSON to get indexable metadata
      const synthesisData = JSON.parse(activeJsonView.jsonResult);
      const brand = synthesisData.brand || null;
      const model = synthesisData.model || null;
      const offer_number =
        synthesisData?.offer_number ||
        synthesisData?.metadata?.offer_number ||
        null;

      // 3. Insert into the JSONB table
      const { error: dbError } = await supabase
        .from("vehicle_synthesis")
        .insert({
          id: fileId,
          brand,
          model,
          offer_number,
          raw_pdf_url: pdfUrl,
          schema_version: "v2.0_digital_twin",
          synthesis_data: synthesisData,
          file_hash: activeJsonView.fileHash,
        });

      if (dbError) {
        console.error("Supabase Database Error Details:", dbError);
        throw new Error("Database insertion failed: " + dbError.message);
      }

      alert("Pomyślnie zapisano dokument i strukturę AI w bazie danych!");
      setActiveJsonView(null);

      if (onSuccessSaved) {
        onSuccessSaved();
      }
    } catch (e: unknown) {
      console.error("Full Catch block error:", e);
      const msg = e instanceof Error ? e.message : String(e);
      alert(`Wystąpił błąd podczas zapisywania: ${msg}`);
    } finally {
      setIsSaving(false);
    }
  }, [activeJsonView, onSuccessSaved]);

  const removeDocument = useCallback((id: string) => {
    setDocuments((docs) => docs.filter((d) => d.id !== id));
  }, []);

  const handleOpenSavedJson = useCallback(
    async (vehicleId: string, titleName: string) => {
      try {
        const { data, error } = await supabase
          .from("vehicle_synthesis")
          .select("synthesis_data")
          .eq("id", vehicleId)
          .single();

        if (error) throw error;

        setActiveJsonView({
          id: vehicleId,
          name: titleName,
          size: 0,
          type: "pdf",
          status: "completed",
          jsonResult: JSON.stringify(data.synthesis_data, null, 2),
        });
      } catch (err) {
        console.error("Failed to load saved JSON", err);
        alert("Błąd podczas ładowania struktury JSON z bazy.");
      }
    },
    [],
  );

  return {
    documents,
    activeJsonView,
    setActiveJsonView,
    isSaving,
    handleFiles,
    handleSaveToDatabase,
    handleOpenSavedJson,
    removeDocument,
  };
}
