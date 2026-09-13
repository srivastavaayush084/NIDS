import { useState, useEffect, useCallback, useRef } from 'react';
import { statisticsApi } from '../api/statistics';
import { POLLING_INTERVAL_MS } from '../utils/constants';

export function useStatistics(intervalMs = POLLING_INTERVAL_MS) {
  const [summary, setSummary] = useState(null);
  const [alertStats, setAlertStats] = useState(null);
  const [modelStats, setModelStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMounted = useRef(true);

  const fetchStats = useCallback(async () => {
    try {
      const [sumRes, altRes, modRes] = await Promise.allSettled([
        statisticsApi.getDashboardSummary(),
        statisticsApi.getAlertStatistics(),
        statisticsApi.getModelStatistics(),
      ]);

      if (!isMounted.current) return;

      if (sumRes.status === 'fulfilled') {
        setSummary(sumRes.value);
        setError(null);
      } else {
        setError(sumRes.reason?.message || 'Failed to fetch dashboard summary');
      }

      if (altRes.status === 'fulfilled') {
        setAlertStats(altRes.value);
      }

      if (modRes.status === 'fulfilled') {
        setModelStats(modRes.value);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err.message || 'Error fetching statistics');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    fetchStats();

    let intervalId = null;
    if (intervalMs > 0) {
      intervalId = setInterval(fetchStats, intervalMs);
    }

    return () => {
      isMounted.current = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchStats, intervalMs]);

  return {
    summary,
    alertStats,
    modelStats,
    loading,
    error,
    refetch: fetchStats,
  };
}

export default useStatistics;
