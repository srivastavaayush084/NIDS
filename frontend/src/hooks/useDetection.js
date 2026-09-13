import { useState, useEffect, useCallback, useRef } from 'react';
import { detectionApi } from '../api/detection';
import { POLLING_INTERVAL_MS } from '../utils/constants';

export function useDetection(initialParams = {}, autoPoll = false) {
  const [detections, setDetections] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 1,
  });
  const [params, setParams] = useState(initialParams);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMounted = useRef(true);

  const fetchDetections = useCallback(async () => {
    try {
      setLoading(true);
      const res = await detectionApi.getDetections(params);
      if (!isMounted.current) return;

      if (res && res.data) {
        setDetections(res.data);
        if (res.pagination) {
          setPagination(res.pagination);
        }
        setError(null);
      } else {
        setDetections([]);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err.message || 'Failed to fetch detection history');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, [params]);

  useEffect(() => {
    isMounted.current = true;
    fetchDetections();

    let intervalId = null;
    if (autoPoll && POLLING_INTERVAL_MS > 0) {
      intervalId = setInterval(fetchDetections, POLLING_INTERVAL_MS);
    }

    return () => {
      isMounted.current = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchDetections, autoPoll]);

  const updateFilters = (newFilters) => {
    setParams((prev) => ({
      ...prev,
      ...newFilters,
      page: 1,
    }));
  };

  const setPage = (newPage) => {
    setParams((prev) => ({
      ...prev,
      page: newPage,
    }));
  };

  return {
    detections,
    pagination,
    params,
    loading,
    error,
    refetch: fetchDetections,
    updateFilters,
    setPage,
  };
}

export default useDetection;
