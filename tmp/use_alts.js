
export function useVehicleAlternatives(
  vehicleId: string,
  durationMonths: number,
  annualMileage: number,
  category: string,
  enabled: boolean
): { alternatives: SimilarVehicle[]; loading: boolean } {
  const [alternatives, setAlternatives] = useState<SimilarVehicle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !vehicleId || !category) {
      setAlternatives([]);
      return;
    }
    let cancelled = false;
    const doFetch = async () => {
      setLoading(true);
      try {
        const queryParams = new URLSearchParams({
          category,
          duration_months: durationMonths.toString(),
          annual_mileage: annualMileage.toString(),
          limit: '5'
        });
        const r = await apiClient.fetch(`/api/scoring-search/vehicle/${vehicleId}/alternatives?${queryParams}`);
        const data = await r.json();
        if (!cancelled) setAlternatives(data.results || []);
      } catch {
        if (!cancelled) setAlternatives([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    doFetch();
    return () => { 
      cancelled = true; 
    };
  }, [vehicleId, durationMonths, annualMileage, category, enabled]);

  return { alternatives, loading };
}
