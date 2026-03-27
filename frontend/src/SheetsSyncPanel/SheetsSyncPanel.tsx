import { useState, useCallback } from "react";
import "./SheetsSyncPanel.css";

// ── Types ──────────────────────────────────────────────────────────────────

interface SheetInfo {
  title: string;
  row_count: number;
  col_count: number;
  headers: string[];
}

interface SpreadsheetInfo {
  spreadsheet_id: string;
  title: string;
  sheets: SheetInfo[];
}

interface AvailableTable {
  table_name: string;
  label: string;
}

interface ColumnMapping {
  sheet_col: string;
  db_col: string;
  transform: "str" | "int" | "float" | "bool";
}

interface SyncResult {
  status: string;
  table: string;
  sheet: string;
  rows_fetched: number;
  rows_upserted: number;
  rows_skipped: number;
  errors: string[];
}

const BACKEND = import.meta.env.VITE_API_URL || "http://localhost:8000";
const SPREADSHEET_DEFAULT =
  "1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q";

// ── API helpers ────────────────────────────────────────────────────────────

async function fetchJson<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem("sb-token") ?? "";
  const res = await fetch(url, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...opts?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function MappingEditor({
  sheet,
  dbTables,
  onSync,
}: {
  sheet: SheetInfo;
  dbTables: AvailableTable[];
  onSync: (result: SyncResult) => void;
}) {
  const [selectedTable, setSelectedTable] = useState("");
  const [upsertCol, setUpsertCol] = useState("id");
  const [mappings, setMappings] = useState<ColumnMapping[]>(() =>
    sheet.headers.map((h) => ({
      sheet_col: h,
      db_col: h.toLowerCase().replace(/\s+/g, "_"),
      transform: "str",
    }))
  );
  const [loading, setLoading] = useState(false);
  const [spreadsheetId, setSpreadsheetId] = useState(SPREADSHEET_DEFAULT);

  const updateMapping = (
    idx: number,
    field: keyof ColumnMapping,
    value: string
  ) => {
    setMappings((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: value } as ColumnMapping;
      return next;
    });
  };

  const handleSync = async () => {
    if (!selectedTable) return;
    setLoading(true);
    try {
      const result = await fetchJson<SyncResult>(`${BACKEND}/api/sheets/sync`, {
        method: "POST",
        body: JSON.stringify({
          spreadsheet_id: spreadsheetId,
          sheet_name: sheet.title,
          db_table: selectedTable,
          column_mappings: mappings.filter((m) => m.db_col.trim() !== ""),
          upsert_conflict_column: upsertCol,
        }),
      });
      onSync(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      onSync({
        status: "error",
        table: selectedTable,
        sheet: sheet.title,
        rows_fetched: 0,
        rows_upserted: 0,
        rows_skipped: 0,
        errors: [msg],
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ssp-mapping-editor">
      <h4 className="ssp-sheet-title">
        📋 {sheet.title}
        <span className="ssp-pill">{sheet.headers.length} kolumn</span>
      </h4>

      <div className="ssp-row">
        <label>Spreadsheet ID</label>
        <input
          className="ssp-input"
          value={spreadsheetId}
          onChange={(e) => setSpreadsheetId(e.target.value)}
          placeholder="ID arkusza Google"
        />
      </div>

      <div className="ssp-row">
        <label>Tabela Supabase →</label>
        <select
          className="ssp-select"
          value={selectedTable}
          onChange={(e) => setSelectedTable(e.target.value)}
        >
          <option value="">-- wybierz tabelę --</option>
          {dbTables.map((t) => (
            <option key={t.table_name} value={t.table_name}>
              {t.label} ({t.table_name})
            </option>
          ))}
        </select>
      </div>

      <div className="ssp-row">
        <label>Kolumna konfliktu (upsert)</label>
        <input
          className="ssp-input ssp-input-sm"
          value={upsertCol}
          onChange={(e) => setUpsertCol(e.target.value)}
        />
      </div>

      <div className="ssp-mapping-table-wrap">
        <table className="ssp-mapping-table">
          <thead>
            <tr>
              <th>Kolumna w arkuszu</th>
              <th>Mapuj na kolumnę DB</th>
              <th>Typ</th>
              <th>✕</th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((m, i) => (
              <tr key={i} className={m.db_col.trim() === "" ? "ssp-row-skip" : ""}>
                <td>
                  <span className="ssp-sheet-col">{m.sheet_col}</span>
                </td>
                <td>
                  <input
                    className="ssp-input ssp-input-sm"
                    value={m.db_col}
                    onChange={(e) => updateMapping(i, "db_col", e.target.value)}
                    placeholder="pomiń (zostaw puste)"
                  />
                </td>
                <td>
                  <select
                    className="ssp-select ssp-select-sm"
                    value={m.transform}
                    onChange={(e) => updateMapping(i, "transform", e.target.value)}
                  >
                    <option value="str">str</option>
                    <option value="int">int</option>
                    <option value="float">float</option>
                    <option value="bool">bool</option>
                  </select>
                </td>
                <td>
                  <button
                    className="ssp-btn-icon"
                    onClick={() =>
                      setMappings((prev) => prev.filter((_, j) => j !== i))
                    }
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        className="ssp-btn-sync"
        disabled={!selectedTable || loading}
        onClick={handleSync}
      >
        {loading ? "⏳ Synchronizuję..." : `🔄 Sync → ${selectedTable || "?"}`}
      </button>
    </div>
  );
}

function SyncResultBadge({ result }: { result: SyncResult }) {
  const ok = result.status === "success" || result.status === "partial";
  return (
    <div className={`ssp-result ${ok ? "ssp-result-ok" : "ssp-result-err"}`}>
      <strong>{ok ? "✅" : "❌"} {result.sheet} → {result.table}</strong>
      <span>
        {result.rows_fetched} wierszy | {result.rows_upserted} upserted |{" "}
        {result.rows_skipped} skipped
      </span>
      {result.errors.length > 0 && (
        <ul className="ssp-errors">
          {result.errors.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Main Panel ─────────────────────────────────────────────────────────────

export default function SheetsSyncPanel() {
  const [spreadsheetId, setSpreadsheetId] = useState(SPREADSHEET_DEFAULT);
  const [inspecting, setInspecting] = useState(false);
  const [spreadsheetInfo, setSpreadsheetInfo] = useState<SpreadsheetInfo | null>(null);
  const [dbTables, setDbTables] = useState<AvailableTable[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SyncResult[]>([]);
  const [activeSheet, setActiveSheet] = useState<string | null>(null);

  const handleInspect = useCallback(async () => {
    setInspecting(true);
    setError(null);
    try {
      const [info, tables] = await Promise.all([
        fetchJson<SpreadsheetInfo>(
          `${BACKEND}/api/sheets/inspect?spreadsheet_id=${encodeURIComponent(spreadsheetId)}`
        ),
        fetchJson<AvailableTable[]>(`${BACKEND}/api/sheets/tables`),
      ]);
      setSpreadsheetInfo(info);
      setDbTables(tables);
      if (info.sheets.length > 0) setActiveSheet(info.sheets[0].title);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setInspecting(false);
    }
  }, [spreadsheetId]);

  const handleSyncResult = useCallback((r: SyncResult) => {
    setResults((prev) => [r, ...prev].slice(0, 20));
  }, []);

  const activeSheetInfo = spreadsheetInfo?.sheets.find(
    (s) => s.title === activeSheet
  );

  return (
    <div className="ssp-panel">
      <div className="ssp-header">
        <h2>🔗 Google Sheets Sync</h2>
        <p className="ssp-subtitle">
          Wybierz arkusz, zmapuj kolumny i zsynchronizuj do Supabase
        </p>
      </div>

      {/* Step 1: Spreadsheet URL */}
      <div className="ssp-card">
        <h3>Krok 1: Podaj ID arkusza Google</h3>
        <div className="ssp-row">
          <input
            id="spreadsheetIdInput"
            className="ssp-input ssp-input-full"
            value={spreadsheetId}
            onChange={(e) => setSpreadsheetId(e.target.value)}
            placeholder="np. 1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q"
          />
          <button
            className="ssp-btn-primary"
            onClick={handleInspect}
            disabled={inspecting || !spreadsheetId.trim()}
          >
            {inspecting ? "⏳ Ładowanie..." : "🔍 Wczytaj arkusz"}
          </button>
        </div>
        {error && <div className="ssp-error-box">❌ {error}</div>}
      </div>

      {/* Step 2: Sheet tabs */}
      {spreadsheetInfo && (
        <div className="ssp-card">
          <h3>
            Krok 2: Wybierz zakładkę —{" "}
            <em>{spreadsheetInfo.title}</em>
          </h3>
          <div className="ssp-tabs">
            {spreadsheetInfo.sheets.map((s) => (
              <button
                key={s.title}
                className={`ssp-tab ${activeSheet === s.title ? "ssp-tab-active" : ""}`}
                onClick={() => setActiveSheet(s.title)}
              >
                {s.title}
                <span className="ssp-tab-count">{s.headers.length}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 3: Mapping editor */}
      {activeSheetInfo && (
        <div className="ssp-card">
          <h3>Krok 3: Mapuj kolumny → tabela Supabase</h3>
          <MappingEditor
            key={activeSheetInfo.title}
            sheet={activeSheetInfo}
            dbTables={dbTables}
            onSync={handleSyncResult}
          />
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="ssp-card">
          <h3>📊 Historia synchronizacji</h3>
          {results.map((r, i) => (
            <SyncResultBadge key={i} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}
