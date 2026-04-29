import { useEffect, useState } from 'react';
import { apiClient } from '../../lib/apiClient';
import type { InitialDataResponse } from '../types';

export function useInitialData() {
  const [initialData, setInitialData] = useState<InitialDataResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await apiClient.fetch('/api/scoring-search/initial-data', { method: 'GET' });
        if (!res.ok) return;
        const json = await res.json();
        if (!cancelled) setInitialData(json.data || json);
      } catch (err) {
        if (!cancelled) console.error('initial-data fetch failed', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { initialData, loading };
}
