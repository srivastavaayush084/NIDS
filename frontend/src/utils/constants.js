export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const POLLING_INTERVAL_MS = Number(import.meta.env.VITE_POLLING_INTERVAL_MS) || 5000;

export const SEVERITY_TIERS = {
  LOW: {
    label: 'LOW',
    color: '#3b82f6',
    bg: 'rgba(59, 130, 246, 0.15)',
    border: 'rgba(59, 130, 246, 0.35)',
    badgeClass: 'badge-low',
  },
  MEDIUM: {
    label: 'MEDIUM',
    color: '#eab308',
    bg: 'rgba(234, 179, 8, 0.15)',
    border: 'rgba(234, 179, 8, 0.35)',
    badgeClass: 'badge-medium',
  },
  HIGH: {
    label: 'HIGH',
    color: '#f97316',
    bg: 'rgba(249, 115, 22, 0.15)',
    border: 'rgba(249, 115, 22, 0.35)',
    badgeClass: 'badge-high',
  },
  CRITICAL: {
    label: 'CRITICAL',
    color: '#ef4444',
    bg: 'rgba(239, 68, 68, 0.18)',
    border: 'rgba(239, 68, 68, 0.45)',
    badgeClass: 'badge-critical',
  },
};

export const STATUS_COLORS = {
  OPEN: '#ef4444',
  ACKNOWLEDGED: '#f97316',
  RESOLVED: '#10b981',
  DISMISSED: '#64748b',
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
