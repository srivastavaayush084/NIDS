import { useState, useEffect, useCallback, useRef } from 'react';
import { healthApi } from '../api/health';
import { POLLING_INTERVAL_MS } from '../utils/constants';

export function useHealth(intervalMs = POLLING_INTERVAL_MS) {
  const [health, setHealth] = useState(null);
  const [detailed, setDetailed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMounted = useRef(true);

  const fetchHealth = useCallback(async () => {
    try {
      const [hData, dData] = await Promise.allSettled([
        healthApi.getHealth(),
        healthApi.getDetailedHealth(),
      ]);

      if (!isMounted.current) return;

      if (hData.status === 'fulfilled') {
        setHealth(hData.value);
        setError(null);
      } else {
        setError(hData.reason?.message || 'Failed to fetch health');
      }

      if (dData.status === 'fulfilled') {
        setDetailed(dData.value);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err.message || 'Health check error');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    fetchHealth();

    let intervalId = null;
    if (intervalMs > 0) {
      intervalId = setInterval(fetchHealth, intervalMs);
    }

    return () => {
      isMounted.current = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchHealth, intervalMs]);

  return {
    health,
    detailed,
    loading,
    error,
    refetch: fetchHealth,
  };
}

export default useHealth;
