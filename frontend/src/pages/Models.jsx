import React from 'react';
import { useModels } from '../hooks/useModels';
import { ModelCard } from '../components/models/ModelCard';
import { ModelComparisonTable } from '../components/models/ModelComparisonTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { Cpu, RefreshCw, Layers } from 'lucide-react';

export function Models() {
  const { models, comparison, loading, error, refetch } = useModels('synthetic');

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-[#0F172A] uppercase tracking-wide flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-[#2563EB]" />
            <span>AI Model Registry & Comparison</span>
          </h2>
          <p className="text-xs text-[#64748B] mt-1">
            Registered machine learning anomaly detection models, hyperparameter configurations, and zero-day benchmark evaluation matrices.
          </p>
        </div>

        <button
          onClick={refetch}
          disabled={loading}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-[#0F172A] text-xs font-semibold border border-[#CBD5E1] shadow-2xs transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#2563EB]' : 'text-[#64748B]'}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onRetry={refetch} />}

      {/* Model Cards Grid */}
      {loading && models.length === 0 ? (
        <LoadingSpinner message="Loading Model Registry metadata..." className="py-16" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {(models.length > 0
            ? models
            : [
                { name: 'isolation_forest', version: '1.0.0', threshold: 50.0, is_trained: true },
                { name: 'autoencoder', version: '1.0.0', threshold: 1.0788, is_trained: true },
                { name: 'lstm_autoencoder', version: '1.0.0', threshold: 0.6586, is_trained: true },
                { name: 'random_forest', version: '1.0.0', threshold: 0.1000, is_trained: true },
                { name: 'ensemble', version: '1.0.0', threshold: 50.0, is_trained: true },
              ]
          ).map((m, idx) => (
            <ModelCard key={idx} model={m} />
          ))}
        </div>
      )}

      {/* Comparative Evaluation Benchmark Matrix */}
      <ModelComparisonTable comparisonData={comparison} />
    </div>
  );
}

export default Models;
