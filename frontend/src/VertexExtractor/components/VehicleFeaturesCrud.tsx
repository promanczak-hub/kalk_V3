import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { apiClient } from "../../lib/apiClient";

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

  // New Feature Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [newFeature, setNewFeature] = useState<{name: string; type: 'boolean'|'numeric'|'text'; valBool: boolean; valNum: string; valText: string}>({
    name: '', type: 'boolean', valBool: true, valNum: '', valText: ''
  });

  // ── Fetch features ─────────────────────────────────────
  const fetchFeatures = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.fetch(`/api/vehicles/${vehicleId}/features`);
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

  const handleEditBool = (featureKey: string, currentVal: boolean | null) => {
    const val = currentVal === null ? true : !currentVal;
    setEditBuffer(prev => ({
      ...prev,
      [featureKey]: { ...prev[featureKey], value_bool: val },
    }));
  };

  // ── Add Custom Feature ─────────────────────────────────
  const handleAddCustomFeature = async () => {
    if (!newFeature.name.trim()) return;
    setSaving(true);
    setStatusMessage(null);
    try {
      const payload = {
        feature_key: '_new_manual', // Dummy key; backend will slugify display_name
        is_new_manual: true,
        display_name: newFeature.name.trim(),
        value_bool: newFeature.type === 'boolean' ? newFeature.valBool : null,
        value_num: newFeature.type === 'numeric' && newFeature.valNum ? parseFloat(newFeature.valNum) : null,
        value_text: newFeature.type === 'text' ? newFeature.valText : null
      };

      const res = await apiClient.fetch(`/api/vehicles/${vehicleId}/features`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: [payload] }),
      });
      const data = await res.json();
      
      if (data.upserted > 0) {
        setStatusMessage({ type: 'success', text: `Pomyślnie dodano: ${newFeature.name}` });
        setNewFeature({ name: '', type: 'boolean', valBool: true, valNum: '', valText: '' });
        setShowAddForm(false);
        fetchFeatures();
      }
      if (data.errors?.length) {
        setStatusMessage({ type: 'error', text: data.errors.join(', ') });
      }
    } catch(err) {
      setStatusMessage({ type: 'error', text: `Błąd dodawania cechy: ${err}` });
    } finally {
      setSaving(false);
    }
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
      const res = await apiClient.fetch(`/api/vehicles/${vehicleId}/features`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: payload }),
      });
      const data = await res.json();

      if (data.upserted > 0) {
        setStatusMessage({ type: 'success', text: `Zapisano ${data.upserted} zmian` });
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
    if (!window.confirm(`Czy na pewno usunąć cechę "${featureKey}" z tego pojazdu?`)) return;
    try {
      await apiClient.fetch(`/api/vehicles/${vehicleId}/features/${featureKey}`, {
        method: 'DELETE',
      });
      setFeatures(prev => prev.filter(f => f.feature_key !== featureKey));
      setStatusMessage({ type: 'success', text: `Usunięto pomyślnie z danego pojazdu.` });
    } catch (err) {
      setStatusMessage({ type: 'error', text: `Błąd usuwania cechy: ${err}` });
    }
  };

  // ── Render value cell ──────────────────────────────────
  const renderValue = (f: VehicleFeature) => {
    const edited = editBuffer[f.feature_key];

    if (f.feature_type === 'boolean') {
      const displayVal = edited?.value_bool !== undefined ? edited.value_bool : f.value_bool;
      return (
        <button
          onClick={() => handleEditBool(f.feature_key, displayVal)}
          style={{
            background: 'transparent', border: '1px solid #cbd5e1', color: displayVal ? '#15803d' : '#b91c1c',
            fontWeight: 600, padding: '4px 10px', borderRadius: 6, cursor: 'pointer',
            fontSize: 13, backgroundClip: 'padding-box', backgroundColor: displayVal ? '#dcfce7' : '#fee2e2'
          }}
        >
          {displayVal ? '✅ Tak' : '❌ Nie'}
        </button>
      );
    }

    if (f.feature_type === 'numeric') {
      const displayVal = edited?.value_num !== undefined ? (edited.value_num ?? '') : (f.value_num ?? '');
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            type="number"
            value={displayVal}
            onChange={e => handleEditNum(f.feature_key, e.target.value)}
            className="input-field"
            style={{
              width: 100, padding: '4px 8px',
              background: '#f8fafc', border: '1px solid #cbd5e1',
              borderRadius: 6, color: '#0f172a', fontSize: 13,
            }}
          />
          {f.unit && <span style={{ color: '#64748b', fontSize: 12 }}>{f.unit}</span>}
        </div>
      );
    }

    // text
    const displayText = edited?.value_text !== undefined ? (edited.value_text ?? '') : (f.value_text ?? '');
    return (
      <input
        type="text"
        value={displayText}
        onChange={e => handleEditText(f.feature_key, e.target.value)}
        className="input-field"
        style={{
          width: 220, padding: '4px 8px',
          background: '#f8fafc', border: '1px solid #cbd5e1',
          borderRadius: 6, color: '#0f172a', fontSize: 13,
        }}
      />
    );
  };

  // ── Main render ────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: '#64748b' }}>
        <div className="spinner" style={{ margin: '0 auto 12px' }} />
        Ładowanie cech...
      </div>
    );
  }

  return (
    <div style={{
      padding: '20px 24px', maxHeight: '80vh', overflowY: 'auto',
      background: '#ffffff',
      borderRadius: 12,
      border: '1px solid #e2e8f0',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: 16, flexWrap: 'wrap', gap: 12, borderBottom: '1px solid #f1f5f9', paddingBottom: 16
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, color: '#0f172a', fontWeight: 600 }}>
            ⚙️ Cechy Użytkowe {vehicleName ? `— ${vehicleName}` : ''}
          </h2>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 12 }}>
            <span style={{
              background: '#ecfccb', color: '#4d7c0f',
              padding: '2px 8px', borderRadius: 6, fontWeight: 500
            }}>
              ✅ {stats.boolCount} boolowskich
            </span>
            <span style={{
              background: '#e0f2fe', color: '#0369a1',
              padding: '2px 8px', borderRadius: 6, fontWeight: 500
            }}>
              📐 {stats.numCount} liczbowych
            </span>
            <span style={{
              background: '#f3e8ff', color: '#7e22ce',
              padding: '2px 8px', borderRadius: 6, fontWeight: 500
            }}>
              📝 {stats.textCount} tekstowych
            </span>
            <span style={{ color: '#64748b', fontWeight: 500 }}>
              Razem: {stats.total}
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="panel-btn-close"
            style={{
              background: '#f8fafc', border: '1px solid #e2e8f0',
              color: '#475569', borderRadius: 8, padding: '6px 14px', cursor: 'pointer',
              fontSize: 13, fontWeight: 500
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#f1f5f9'}
            onMouseLeave={e => e.currentTarget.style.background = '#f8fafc'}
          >
            ✕ Zamknij
          </button>
        )}
      </div>

      {/* Action Bar */}
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
            background: '#f8fafc', border: '1px solid #cbd5e1',
            borderRadius: 8, color: '#0f172a', fontSize: 14, outline: 'none',
          }}
        />
        
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #cbd5e1',
            background: '#ffffff', color: '#334155', fontWeight: 500, fontSize: 13, cursor: 'pointer',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
          onMouseLeave={e => e.currentTarget.style.background = '#ffffff'}
        >
          {showAddForm ? '✕ Anuluj' : '➕ Dodaj własną cechę'}
        </button>

        {Object.keys(editBuffer).length > 0 && (
          <button
            onClick={saveChanges}
            disabled={saving}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: '#2563eb', color: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer',
              opacity: saving ? 0.6 : 1, transition: 'background 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#1d4ed8'}
            onMouseLeave={e => e.currentTarget.style.background = '#2563eb'}
          >
            {saving ? '💾 Zapisuję...' : `💾 Zapisz zmiany (${Object.keys(editBuffer).length})`}
          </button>
        )}
      </div>

      {/* Add New Feature Form */}
      {showAddForm && (
        <div style={{
          padding: 16, marginBottom: 16, background: '#f8fafc',
          border: '1px dashed #cbd5e1', borderRadius: 8, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end'
        }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 4 }}>Nazwa nowej cechy</label>
            <input 
              type="text" 
              placeholder="np. Hak holowniczy"
              value={newFeature.name} 
              onChange={e => setNewFeature({...newFeature, name: e.target.value})}
              style={{ padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, minWidth: 200 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 4 }}>Typ wartości</label>
            <select 
              value={newFeature.type} 
              onChange={e => setNewFeature({...newFeature, type: e.target.value as any})}
              style={{ padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
            >
              <option value="boolean">Tak/Nie (Prawda/Fałsz)</option>
              <option value="text">Zwykły Tekst</option>
              <option value="numeric">Liczba</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 4 }}>Wartość</label>
            {newFeature.type === 'boolean' && (
              <select 
                value={String(newFeature.valBool)} 
                onChange={e => setNewFeature({...newFeature, valBool: e.target.value === 'true'})}
                style={{ padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13, background: '#fff' }}
              >
                <option value="true">Tak</option>
                <option value="false">Nie</option>
              </select>
            )}
            {newFeature.type === 'text' && (
              <input 
                type="text" 
                placeholder="Wartość tekstowa"
                value={newFeature.valText} 
                onChange={e => setNewFeature({...newFeature, valText: e.target.value})}
                style={{ padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
              />
            )}
            {newFeature.type === 'numeric' && (
              <input 
                type="number" 
                placeholder="0.00"
                value={newFeature.valNum} 
                onChange={e => setNewFeature({...newFeature, valNum: e.target.value})}
                style={{ padding: '6px 12px', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: 13 }}
              />
            )}
          </div>
          <button 
            onClick={handleAddCustomFeature}
            disabled={saving || !newFeature.name.trim()}
            style={{
              padding: '6px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6,
              fontSize: 13, fontWeight: 600, cursor: saving || !newFeature.name.trim() ? 'not-allowed' : 'pointer',
              opacity: saving || !newFeature.name.trim() ? 0.6 : 1, height: 31
            }}
          >
            Dodaj i zapisz
          </button>
        </div>
      )}

      {/* Status message */}
      {statusMessage && (
        <div style={{
          padding: '8px 14px', borderRadius: 8, marginBottom: 16, fontSize: 13, fontWeight: 500,
          background: statusMessage.type === 'success' ? '#dcfce7' : '#fee2e2',
          color: statusMessage.type === 'success' ? '#166534' : '#991b1b',
          border: `1px solid ${statusMessage.type === 'success' ? '#bbf7d0' : '#fecaca'}`,
        }}>
          {statusMessage.text}
        </div>
      )}

      {/* Features by category */}
      {features.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 40, color: '#64748b',
          background: '#f8fafc', borderRadius: 12, border: '1px dashed #cbd5e1'
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
          <div style={{ fontSize: 15, fontWeight: 500, color: '#334155' }}>Brak zidentyfikowanych cech użytkowych</div>
          <div style={{ fontSize: 12, marginTop: 6, color: '#64748b' }}>
            Wykorzystaj panel powyżej, aby ręcznie dodać nową cechę.
          </div>
        </div>
      ) : (
        grouped.map(([catKey, group]) => (
          <div key={catKey} style={{ marginBottom: 24 }}>
            <div style={{
              fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase',
              letterSpacing: 1, marginBottom: 8, paddingBottom: 4,
              borderBottom: '2px solid #f1f5f9',
            }}>
              {group.name} ({group.features.length})
            </div>
            <div style={{
              display: 'grid', gap: 6,
            }}>
              {group.features.map(f => (
                <div
                  key={f.state_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(200px, 1fr) auto auto auto',
                    alignItems: 'center',
                    gap: 12,
                    padding: '8px 12px',
                    borderRadius: 8,
                    background: '#f8fafc',
                    border: '1px solid #f1f5f9',
                    transition: 'border-color 0.15s, box-shadow 0.15s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = '#cbd5e1';
                    e.currentTarget.style.boxShadow = '0 1px 2px 0 rgba(0,0,0,0.05)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#f1f5f9';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: '#0f172a', fontWeight: 600 }}>
                      {f.display_name}
                    </div>
                    <div style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'monospace', marginTop: 2 }}>
                      {f.feature_key}
                    </div>
                  </div>

                  {renderValue(f)}

                  <div style={{
                    fontSize: 11, color: '#64748b', minWidth: 60, textAlign: 'right', fontWeight: 500
                  }}>
                    {Math.round((f.confidence ?? 0) * 100)}%
                    {f.is_manual && <span style={{ color: '#d97706', marginLeft: 4 }} title="Parametr wprowadzony ręcznie">✏️</span>}
                  </div>

                  <button
                    onClick={() => deleteFeature(f.feature_key)}
                    title="Usuń przypisanie cechy z tego pojazdu"
                    style={{
                      background: 'none', border: 'none', color: '#94a3b8',
                      cursor: 'pointer', fontSize: 16, padding: '2px 6px',
                      borderRadius: 4, transition: 'color 0.2s, background 0.2s',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.color = '#ef4444';
                      e.currentTarget.style.background = '#fee2e2';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.color = '#94a3b8';
                      e.currentTarget.style.background = 'none';
                    }}
                  >
                    ×
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
