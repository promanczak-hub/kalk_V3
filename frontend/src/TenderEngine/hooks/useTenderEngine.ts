import { useState, useCallback, useRef } from 'react';
import { apiClient } from '../../lib/apiClient';

// ── Types ──

export type TenderPriority = 'MUST' | 'SHOULD' | 'NICE';
export type ComplianceStatus = 'PASS' | 'FAIL' | 'MISSING';
export type VehicleComplianceStatus = 'MATCH' | 'NOT_COMPLIANT' | 'MISSING_DATA';

export interface FeatureDictionaryEntry {
  id: string;
  feature_key: string;
  technical_key: string | null;
  display_name: string;
  category: string | null;
  feature_type: string;
  feature_tier: 'CORE' | 'EXTENDED' | 'EDGE' | null;
  canonical_unit: string | null;
  is_filterable: boolean;
  is_tender_criteria: boolean;
  is_comparable: boolean;
  body_context: string;
  visibility_group: string | null;
}

export interface TenderCriterion {
  id: string; // local client-side id for keying
  feature_key: string;
  operator: '>=' | '<=' | '>' | '<' | '=' | '!=' | 'IN';
  value: number | string | boolean;
  priority: TenderPriority;
  display_name?: string;
}

export interface CriterionResult {
  feature_key: string;
  feature_name: string | null;
  required_operator: string;
  required_value: string;
  actual_value: number | string | boolean | null;
  status: ComplianceStatus;
  source: string | null;
  confidence: number | null;
}

export interface VehicleTenderResult {
  vehicle_id: string;
  vehicle_label: string;
  compliance_status: VehicleComplianceStatus;
  compliance_score: number;
  criteria_results: CriterionResult[];
  must_pass_count: number;
  must_fail_count: number;
  should_pass_count: number;
  nice_pass_count: number;
}

export interface TenderEvaluateResponse {
  total_vehicles: number;
  match_count: number;
  not_compliant_count: number;
  missing_data_count: number;
  results: VehicleTenderResult[];
}

// ── Hook ──

let nextCriterionId = 1;

export function useTenderEngine() {
  const [dictionary, setDictionary] = useState<FeatureDictionaryEntry[]>([]);
  const [criteria, setCriteria] = useState<TenderCriterion[]>([]);
  const [results, setResults] = useState<TenderEvaluateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingDict, setIsLoadingDict] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchDictionary = useCallback(async () => {
    setIsLoadingDict(true);
    try {
      const data = await apiClient.get<FeatureDictionaryEntry[]>('/api/tender/criteria');
      setDictionary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Błąd pobierania słownika cech');
    } finally {
      setIsLoadingDict(false);
    }
  }, []);

  const addCriterion = useCallback((featureKey: string, displayName?: string) => {
    const id = `criterion_${nextCriterionId++}`;
    setCriteria(prev => [
      ...prev,
      {
        id,
        feature_key: featureKey,
        operator: '=',
        value: true,
        priority: 'MUST',
        display_name: displayName,
      },
    ]);
  }, []);

  const updateCriterion = useCallback((id: string, updates: Partial<TenderCriterion>) => {
    setCriteria(prev =>
      prev.map(c => (c.id === id ? { ...c, ...updates } : c))
    );
  }, []);

  const removeCriterion = useCallback((id: string) => {
    setCriteria(prev => prev.filter(c => c.id !== id));
  }, []);

  const clearCriteria = useCallback(() => {
    setCriteria([]);
    setResults(null);
    setError(null);
  }, []);

  const evaluate = useCallback(async () => {
    if (criteria.length === 0) {
      setError('Dodaj przynajmniej jedno kryterium');
      return;
    }

    // Abort previous
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const payload = {
        criteria: criteria.map(c => ({
          feature_key: c.feature_key,
          operator: c.operator,
          value: c.value,
          priority: c.priority,
        })),
        vehicle_ids: null,
      };

      const data = await apiClient.post<TenderEvaluateResponse>(
        '/api/tender/evaluate',
        payload,
        { signal: controller.signal, skipGlobalError: true }
      );
      setResults(data);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'Błąd oceny przetargowej');
    } finally {
      setIsLoading(false);
    }
  }, [criteria]);

  const uploadFile = useCallback(async (file: File) => {
    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.fetch('/api/tender/upload', {
        method: 'POST',
        body: formData,
        skipGlobalError: true,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data: TenderEvaluateResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Błąd importu pliku');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    dictionary,
    criteria,
    results,
    isLoading,
    isLoadingDict,
    error,
    fetchDictionary,
    addCriterion,
    updateCriterion,
    removeCriterion,
    clearCriteria,
    evaluate,
    uploadFile,
    setError,
  };
}
