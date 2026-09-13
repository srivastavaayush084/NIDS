import React, { useState } from 'react';
import { Search, Filter, RotateCcw } from 'lucide-react';

export function AlertFilters({
  filters = {},
  onFilterChange,
  onReset,
}) {
  const [localFilters, setLocalFilters] = useState({
    severity: filters.severity || '',
    status: filters.status || '',
    source_ip: filters.source_ip || '',
    destination_ip: filters.destination_ip || '',
    min_risk_score: filters.min_risk_score || '',
  });

  const handleChange = (field, value) => {
    const updated = { ...localFilters, [field]: value };
    setLocalFilters(updated);
    onFilterChange(updated);
  };

  const handleReset = () => {
    const cleared = {
      severity: '',
      status: '',
      source_ip: '',
      destination_ip: '',
      min_risk_score: '',
    };
    setLocalFilters(cleared);
    if (onReset) onReset();
    else onFilterChange(cleared);
  };

  return (
    <div className="p-4 rounded-xl border border-white/10 bg-slate-900/60 flex flex-wrap items-center gap-3 text-xs">
      {/* Severity Select */}
      <div className="flex items-center gap-1.5 min-w-[130px]">
        <label className="text-slate-400 text-[11px] font-semibold uppercase">Severity:</label>
        <select
          value={localFilters.severity}
          onChange={(e) => handleChange('severity', e.target.value)}
          className="bg-slate-800 border border-white/10 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
      </div>

      {/* Status Select */}
      <div className="flex items-center gap-1.5 min-w-[140px]">
        <label className="text-slate-400 text-[11px] font-semibold uppercase">Status:</label>
        <select
          value={localFilters.status}
          onChange={(e) => handleChange('status', e.target.value)}
          className="bg-slate-800 border border-white/10 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
        >
          <option value="">All</option>
          <option value="OPEN">OPEN</option>
          <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
          <option value="RESOLVED">RESOLVED</option>
          <option value="DISMISSED">DISMISSED</option>
        </select>
      </div>

      {/* Source IP Input */}
      <div className="relative min-w-[140px]">
        <input
          type="text"
          placeholder="Filter Source IP"
          value={localFilters.source_ip}
          onChange={(e) => handleChange('source_ip', e.target.value)}
          className="w-full bg-slate-800 border border-white/10 rounded-lg px-2.5 py-1.5 font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Destination IP Input */}
      <div className="relative min-w-[140px]">
        <input
          type="text"
          placeholder="Filter Dest IP"
          value={localFilters.destination_ip}
          onChange={(e) => handleChange('destination_ip', e.target.value)}
          className="w-full bg-slate-800 border border-white/10 rounded-lg px-2.5 py-1.5 font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Min Risk Score Input */}
      <div className="flex items-center gap-1.5">
        <label className="text-slate-400 text-[11px] font-semibold uppercase">Min Risk:</label>
        <input
          type="number"
          min="0"
          max="100"
          placeholder="0"
          value={localFilters.min_risk_score}
          onChange={(e) => handleChange('min_risk_score', e.target.value)}
          className="w-16 bg-slate-800 border border-white/10 rounded-lg px-2 py-1.5 font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Reset Action */}
      <button
        onClick={handleReset}
        className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Reset</span>
      </button>
    </div>
  );
}

export default AlertFilters;
