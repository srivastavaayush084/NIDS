import { useState, useEffect, useCallback, useRef } from 'react';
import { modelsApi } from '../api/models';

export function useModels(dataset = 'synthetic') {
  const [models, setModels] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMounted = useRef(true);

  const fetchModels = useCallback(async () => {
    try {
      setLoading(true);
      const [mRes, cRes] = await Promise.allSettled([
        modelsApi.getModels(dataset),
        modelsApi.getModelComparison(dataset),
      ]);

      if (!isMounted.current) return;

      if (mRes.status === 'fulfilled' && mRes.value?.data) {
        setModels(mRes.value.data);
        setError(null);
      } else {
        setModels([]);
      }

      if (cRes.status === 'fulfilled' && cRes.value?.data) {
        setComparison(cRes.value.data);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err.message || 'Failed to fetch model registry');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, [dataset]);

  useEffect(() => {
    isMounted.current = true;
    fetchModels();

    return () => {
      isMounted.current = false;
    };
  }, [fetchModels]);

  return {
    models,
    comparison,
    loading,
    error,
    refetch: fetchModels,
  };
}

export default useModels;
