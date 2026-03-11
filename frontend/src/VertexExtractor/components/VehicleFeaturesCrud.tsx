import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { API_BASE_URL } from '../../config/env';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface VehicleFeature {
  state_id: string;
  feature_id: string;
  feature_key: string;
  display_name: string;
  feature_type: string;       // "boolean" | "numeric" | "text"
  category_key: string;
  category_name: string;
  resolved_status: string;
  value_bool: boolean | null;
  value_num: number | null;
  value_text: string | null;
  unit: string | null;
  confidence: number;
  source: string;
  is_manual: boolean;
}

interface Props {
  vehicleId: string;
  vehicleName?: string;
  onClose?: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

const VehicleFeaturesCrud: React.FC<Props> = ({ vehicleId, vehicleName, onClose }) => {
  const [features, setFeatures] = useState<VehicleFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [editBuffer, setEditBuffer] = useState<Record<string, {
    value_bool?: boolean | null;
    value_num?: number | null;
    value_text?: string | null;
  }>>({});
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // ── Fetch features ─────────────────────────────────────
  const fetchFeatures = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/vehicles/${vehicleId}/features`);
      const data = await res.json();
      setFeatures(data.features || []);
    } catch (err) {
      console.error('Failed to fetch features:', err);
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => {
    fetchFeatures();
  }, [fetchFeatures]);

  // ── Filtered & grouped features ────────────────────────
  const filteredFeatures = useMemo(() => {
    if (!searchQuery.trim()) return features;
    const q = searchQuery.toLowerCase();
    return features.filter(
      f =>
        f.display_name.toLowerCase().includes(q) ||
        f.feature_key.toLowerCase().includes(q) ||
        f.category_name.toLowerCase().includes(q) ||
        (f.value_text || '').toLowerCase().includes(q)
    );
  }, [features, searchQuery]);

  const grouped = useMemo(() => {
    const map: Record<string, { name: string; features: VehicleFeature[] }> = {};
    for (const f of filteredFeatures) {
      const key = f.category_key || '_other';
      if (!map[key]) map[key] = { name: f.category_name || 'Inne', features: [] };
      map[key].features.push(f);
    }
    return Object.entries(map).sort(([, a], [, b]) => a.name.localeCompare(b.name, 'pl'));
  }, [filteredFeatures]);

  // ── Stats ──────────────────────────────────────────────
  const stats = useMemo(() => {
    const boolCount = features.filter(f => f.feature_type === 'boolean').length;
    const numCount = features.filter(f => f.feature_type === 'numeric').length;
    const textCount = features.filter(f => f.feature_type === 'text').length;
    return { total: features.length, boolCount, numCount, textCount };
  }, [features]);

  // ── Edit handlers ──────────────────────────────────────
  const handleEditNum = (featureKey: string, raw: string) => {
    const parsed = raw === '' ? null : parseFloat(raw);
    setEditBuffer(prev => ({
      ...prev,
      [featureKey]: { ...prev[featureKey], value_num: parsed },
    }));
  };

  const handleEditText = (featureKey: string, val: string) => {
    setEditBuffer(prev => ({
      ...prev,
      [featureKey]: { ...prev[featureKey], value_text: val || null },
    }));
  };

  // ── Save changes ───────────────────────────────────────
  const saveChanges = async () => {
    const keys = Object.keys(editBuffer);
    if (!keys.length) return;

    setSaving(true);
    setStatusMessage(null);

    const payload = keys.map(fk => ({
      feature_key: fk,
      ...editBuffer[fk],
    }));

    try {
      const res = await fetch(`${API_BASE_URL}/vehicles/${vehicleId}/features`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: payload }),
      });
      const data = await res.json();

      if (data.upserted > 0) {
        setStatusMessage({ type: 'success', text: `Zapisano ${data.upserted} cech` });
        setEditBuffer({});
        fetchFeatures();
      }
      if (data.errors?.length) {
        setStatusMessage({ type: 'error', text: data.errors.join(', ') });
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Błąd zapisu: ${err}` });
    } finally {
      setSaving(false);
    }
  };

  // ── Delete feature ─────────────────────────────────────
  const deleteFeature = async (featureKey: string) => {
    try {
      await fetch(`${API_BASE_URL}/vehicles/${vehicleId}/features/${featureKey}`, {
        method: 'DELETE',
      });
      setFeatures(prev => prev.filter(f => f.feature_key !== featureKey));
      setStatusMessage({ type: 'success', text: `Usunięto: ${featureKey}` });
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Błąd usuwania: ${err}` });
    }
  };

  // ── Render value cell ──────────────────────────────────
  const renderValue = (f: VehicleFeature) => {
    const edited = editBuffer[f.feature_key];

    if (f.feature_type === 'boolean') {
      return (
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          color: f.value_bool ? '#4ade80' : '#f87171',
          fontWeight: 600,
        }}>
          {f.value_bool ? '✅ Tak' : '❌ Nie'}
        </span>
      );
    }

    if (f.feature_type === 'numeric') {
      const displayVal = edited?.value_num !== undefined
        ? (edited.value_num ?? '')
        : (f.value_num ?? '');
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            type="number"
            value={displayVal}
            onChange={e => handleEditNum(f.feature_key, e.target.value)}
            style={{
              width: 100, padding: '4px 8px',
              background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: 6, color: '#e2e8f0', fontSize: 13,
            }}
          />
          {f.unit && <span style={{ color: '#94a3b8', fontSize: 12 }}>{f.unit}</span>}
        </div>
      );
    }

    // text
    const displayText = edited?.value_text !== undefined
      ? (edited.value_text ?? '')
      : (f.value_text ?? '');
    return (
      <input
        type="text"
        value={displayText}
        onChange={e => handleEditText(f.feature_key, e.target.value)}
        style={{
          width: 200, padding: '4px 8px',
          background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)',
          borderRadius: 6, color: '#e2e8f0', fontSize: 13,
        }}
      />
    );
  };

  // ── Main render ────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: '#94a3b8' }}>
        <div className="spinner" style={{ margin: '0 auto 12px' }} />
        Ładowanie cech pojazdu...
      </div>
    );
  }

  return (
    <div style={{
      padding: '20px 24px', maxHeight: '80vh', overflowY: 'auto',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
      borderRadius: 12,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: 16, flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, color: '#e2e8f0' }}>
            ⚙️ Cechy Użytkowe {vehicleName ? `— ${vehicleName}` : ''}
          </h2>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 12 }}>
            <span style={{
              background: 'rgba(34,197,94,0.15)', color: '#4ade80',
              padding: '2px 8px', borderRadius: 6,
            }}>
              ✅ {stats.boolCount} boolowskich
            </span>
            <span style={{
              background: 'rgba(59,130,246,0.15)', color: '#60a5fa',
              padding: '2px 8px', borderRadius: 6,
            }}>
              📐 {stats.numCount} liczbowych
            </span>
            <span style={{
              background: 'rgba(168,85,247,0.15)', color: '#c084fc',
              padding: '2px 8px', borderRadius: 6,
            }}>
              📝 {stats.textCount} tekstowych
            </span>
            <span style={{ color: '#94a3b8' }}>
              Razem: {stats.total}
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)',
              color: '#94a3b8', borderRadius: 8, padding: '6px 14px', cursor: 'pointer',
              fontSize: 13,
            }}
          >
            ✕ Zamknij
          </button>
        )}
      </div>

      {/* Search + Save bar */}
      <div style={{
        display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap',
      }}>
        <input
          type="text"
          placeholder="🔎 Szukaj cechy..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{
            flex: 1, minWidth: 200, padding: '8px 14px',
            background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 8, color: '#e2e8f0', fontSize: 14, outline: 'none',
          }}
        />
        {Object.keys(editBuffer).length > 0 && (
          <button
            onClick={saveChanges}
            disabled={saving}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              color: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer',
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? '💾 Zapisuję...' : `💾 Zapisz (${Object.keys(editBuffer).length})`}
          </button>
        )}
      </div>

      {/* Status message */}
      {statusMessage && (
        <div style={{
          padding: '8px 14px', borderRadius: 8, marginBottom: 12, fontSize: 13,
          background: statusMessage.type === 'success'
            ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
          color: statusMessage.type === 'success' ? '#4ade80' : '#f87171',
          border: `1px solid ${statusMessage.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
        }}>
          {statusMessage.text}
        </div>
      )}

      {/* Features by category */}
      {features.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 40, color: '#64748b',
          background: 'rgba(255,255,255,0.03)', borderRadius: 12,
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
          <div style={{ fontSize: 15 }}>Brak zidentyfikowanych cech użytkowych</div>
          <div style={{ fontSize: 12, marginTop: 6, color: '#475569' }}>
            Uruchom ekstrakcję cech lub ręcznie dodaj cechy
          </div>
        </div>
      ) : (
        grouped.map(([catKey, group]) => (
          <div key={catKey} style={{ marginBottom: 16 }}>
            <div style={{
              fontSize: 13, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase',
              letterSpacing: 1, marginBottom: 8, paddingBottom: 4,
              borderBottom: '1px solid rgba(255,255,255,0.08)',
            }}>
              {group.name} ({group.features.length})
            </div>
            <div style={{
              display: 'grid', gap: 4,
            }}>
              {group.features.map(f => (
                <div
                  key={f.state_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto auto',
                    alignItems: 'center',
                    gap: 10,
                    padding: '6px 10px',
                    borderRadius: 6,
                    background: 'rgba(255,255,255,0.03)',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 500 }}>
                      {f.display_name}
                    </div>
                    <div style={{ fontSize: 10, color: '#475569', fontFamily: 'monospace' }}>
                      {f.feature_key}
                    </div>
                  </div>

                  {renderValue(f)}

                  <div style={{
                    fontSize: 10, color: '#475569', minWidth: 60, textAlign: 'right',
                  }}>
                    {Math.round((f.confidence ?? 0) * 100)}%
                    {f.is_manual && <span style={{ color: '#f59e0b' }}> ✏️</span>}
                  </div>

                  <button
                    onClick={() => deleteFeature(f.feature_key)}
                    title="Usuń cechę"
                    style={{
                      background: 'none', border: 'none', color: '#475569',
                      cursor: 'pointer', fontSize: 14, padding: '2px 6px',
                      borderRadius: 4,
                    }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
};

export default VehicleFeaturesCrud;
