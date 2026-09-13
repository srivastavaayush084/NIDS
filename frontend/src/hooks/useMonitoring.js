import { useState, useEffect, useCallback, useRef } from 'react';
import { monitoringApi } from '../api/monitoring';
import { POLLING_INTERVAL_MS } from '../utils/constants';

export function useMonitoring(intervalMs = POLLING_INTERVAL_MS) {
  const [status, setStatus] = useState(null);
  const [interfaces, setInterfaces] = useState([]);
  const [driverInfo, setDriverInfo] = useState({ available: true, message: '' });
  const [compatibility, setCompatibility] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const isMounted = useRef(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await monitoringApi.getStatus();
      if (!isMounted.current) return;
      setStatus(res);
      if (res?.available_interfaces?.length) {
        setInterfaces(res.available_interfaces);
      }
      setError(null);
    } catch (err) {
      if (isMounted.current) {
        setError(err.message || 'Error fetching monitoring status');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, []);

  const fetchInterfaces = useCallback(async () => {
    try {
      const res = await monitoringApi.getInterfaces();
      if (!isMounted.current || !res) return;
      if (res.interfaces) setInterfaces(res.interfaces);
      setDriverInfo({
        available: res.driver_available !== false,
        message: res.driver_message || '',
      });
    } catch (err) {
      console.warn('Could not load network interfaces:', err);
    }
  }, []);

  const fetchCompatibility = useCallback(async (dataset = 'synthetic') => {
    try {
      const res = await monitoringApi.getCompatibility(dataset);
      if (isMounted.current && res) {
        setCompatibility(res);
      }
    } catch (err) {
      console.warn('Could not load model compatibility:', err);
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;
    fetchStatus();
    fetchInterfaces();
    fetchCompatibility();

    let intervalId = null;
    if (intervalMs > 0) {
      intervalId = setInterval(fetchStatus, intervalMs);
    }

    return () => {
      isMounted.current = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchStatus, fetchInterfaces, fetchCompatibility, intervalMs]);

  const startMonitoring = async (config) => {
    try {
      setActionLoading(true);
      const res = await monitoringApi.startMonitoring(config);
      setStatus(res);
      return res;
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const stopMonitoring = async () => {
    try {
      setActionLoading(true);
      const res = await monitoringApi.stopMonitoring();
      await fetchStatus();
      return res;
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const testPcap = async (config) => {
    try {
      setActionLoading(true);
      return await monitoringApi.testPcap(config);
    } catch (err) {
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  return {
    status,
    interfaces,
    driverInfo,
    compatibility,
    loading,
    error,
    actionLoading,
    refetch: fetchStatus,
    fetchInterfaces,
    startMonitoring,
    stopMonitoring,
    testPcap,
  };
}

export default useMonitoring;
