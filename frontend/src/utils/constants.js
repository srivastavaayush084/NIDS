export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const POLLING_INTERVAL_MS = Number(import.meta.env.VITE_POLLING_INTERVAL_MS) || 5000;

export const SEVERITY_TIERS = {
  LOW: {
    label: 'LOW',
    color: '#2563EB',
    bg: 'rgba(37, 99, 235, 0.08)',
    border: 'rgba(37, 99, 235, 0.25)',
    badgeClass: 'badge-low',
  },
  MEDIUM: {
    label: 'MEDIUM',
    color: '#F59E0B',
    bg: 'rgba(245, 158, 11, 0.08)',
    border: 'rgba(245, 158, 11, 0.25)',
    badgeClass: 'badge-medium',
  },
  HIGH: {
    label: 'HIGH',
    color: '#F97316',
    bg: 'rgba(249, 115, 22, 0.08)',
    border: 'rgba(249, 115, 22, 0.25)',
    badgeClass: 'badge-high',
  },
  CRITICAL: {
    label: 'CRITICAL',
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.1)',
    border: 'rgba(239, 68, 68, 0.3)',
    badgeClass: 'badge-critical',
  },
};

export const STATUS_COLORS = {
  OPEN: '#EF4444',
  ACKNOWLEDGED: '#F59E0B',
  RESOLVED: '#10B981',
  DISMISSED: '#64748B',
};

export const MODEL_DESCRIPTIONS = {
  isolation_forest: {
    title: 'Isolation Forest',
    type: 'Unsupervised Anomaly Detector',
    description: 'Tree-based partitioning detector optimized for isolating multi-dimensional statistical outliers.',
  },
  autoencoder: {
    title: 'Deep Autoencoder',
    type: 'Reconstruction Anomaly Detector',
    description: 'Dense neural network bottleneck trained on normal traffic to detect anomalous reconstruction errors.',
  },
  lstm_autoencoder: {
    title: 'LSTM Autoencoder',
    type: 'Sequential Temporal Detector',
    description: 'Recurrent sequence network that captures temporal dependencies across consecutive network flows.',
  },
  random_forest: {
    title: 'Random Forest',
    type: 'Supervised Baseline Classifier',
    description: 'Ensemble of decision trees trained on signature attack distributions as a supervised classification baseline.',
  },
  ensemble: {
    title: 'Ensemble Risk Engine',
    type: 'Unified Consensus Engine',
    description: 'Multi-model score normalizer and weighted consensus engine combining point, deep, sequential, and supervised models.',
  },
};
