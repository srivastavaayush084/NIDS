import { useState, useEffect, useCallback, useRef } from 'react';
import { alertsApi } from '../api/alerts';
import { POLLING_INTERVAL_MS } from '../utils/constants';

export function useAlerts(initialParams = {}, autoPoll = true) {
  const [alerts, setAlerts] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 1,
  });
  const [params, setParams] = useState(initialParams);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const isMounted = useRef(true);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const res = await alertsApi.getAlerts(params);
      if (!isMounted.current) return;

      if (res && res.data) {
        setAlerts(res.data);
        if (res.pagination) {
          setPagination(res.pagination);
        }
        setError(null);
      } else {
        setAlerts([]);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err.message || 'Failed to load security alerts');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, [params]);

  useEffect(() => {
    isMounted.current = true;
    fetchAlerts();

    let intervalId = null;
    if (autoPoll && POLLING_INTERVAL_MS > 0) {
      intervalId = setInterval(fetchAlerts, POLLING_INTERVAL_MS);
    }

    return () => {
      isMounted.current = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchAlerts, autoPoll]);

  const updateFilters = (newFilters) => {
    setParams((prev) => ({
      ...prev,
      ...newFilters,
      page: 1, // Reset to page 1 on filter change
    }));
  };

  const setPage = (newPage) => {
    setParams((prev) => ({
      ...prev,
      page: newPage,
    }));
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      setActionLoading(true);
      await alertsApi.acknowledgeAlert(alertId);
      await fetchAlerts();
      return true;
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const resolveAlert = async (alertId, note) => {
    try {
      setActionLoading(true);
      await alertsApi.resolveAlert(alertId, note);
      await fetchAlerts();
      return true;
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const dismissAlert = async (alertId, reason) => {
    try {
      setActionLoading(true);
      await alertsApi.dismissAlert(alertId, reason);
      await fetchAlerts();
      return true;
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  return {
    alerts,
    pagination,
    params,
    loading,
    error,
    actionLoading,
    refetch: fetchAlerts,
    updateFilters,
    setPage,
    acknowledgeAlert,
    resolveAlert,
    dismissAlert,
  };
}

export default useAlerts;
