import React, { useState, useEffect } from 'react';
import { Play, Square, Loader2, Radio, FileText, Settings2, CheckCircle2, AlertCircle, Lock } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function MonitoringControls({
  status = null,
  interfaces = [],
  driverInfo = null,
  onStart,
  onStop,
  loading = false,
}) {
  const { isAnalyst } = useAuth();
  const isRunning = Boolean(status?.running);
  const [source, setSource] = useState('live');
  const [interfaceName, setInterfaceName] = useState('');
  const [filterBpf, setFilterBpf] = useState('tcp or udp');
  const [pcapFile, setPcapFile] = useState('data/sample/sample_network_traffic.pcap');
  const [maxPackets, setMaxPackets] = useState(1000);
  const [replaySpeed, setReplaySpeed] = useState(0.0);
  const datasetName = 'synthetic';
  const generateXai = true;
  const [error, setError] = useState(null);

  // Set default interface when interfaces list is populated
  useEffect(() => {
    if (interfaces?.length && !interfaceName) {
      const defaultIface = interfaces.find((i) => i.is_default);
      if (defaultIface) {
        setInterfaceName(defaultIface.name);
      } else if (interfaces[0]?.name) {
        setInterfaceName(interfaces[0].name);
      }
    }
  }, [interfaces, interfaceName]);

  const handleStart = async (e) => {
    e.preventDefault();
    if (!isAnalyst) {
      setError('Insufficient permissions: Viewer role cannot initiate packet capture.');
      return;
    }
    setError(null);

    const payload = {
      source,
      dataset_name: datasetName,
      max_packets: Number(maxPackets) || 1000,
      generate_xai: generateXai,
    };

    if (source === 'live') {
      payload.interface = interfaceName.trim() || undefined;
      payload.filter = filterBpf.trim() || 'tcp or udp';
    } else {
      if (!pcapFile.trim()) {
        setError('Please specify a valid PCAP file path within allowed data directory.');
        return;
      }
      payload.file = pcapFile.trim();
      payload.replay_speed = Number(replaySpeed) || 0.0;
    }

    try {
      await onStart(payload);
    } catch (err) {
      setError(err.message || 'Failed to start monitoring.');
    }
  };

  const handleStop = async () => {
    if (!isAnalyst) {
      setError('Insufficient permissions: Viewer role cannot terminate packet capture.');
      return;
    }
    setError(null);
    try {
      await onStop();
    } catch (err) {
      setError(err.message || 'Failed to stop monitoring.');
    }
  };

  const isDriverBlocked = source === 'live' && driverInfo && !driverInfo.available;
  const startDisabled = loading || !isAnalyst || isDriverBlocked;
  const startTitle = !isAnalyst
    ? 'Action requires Analyst or Admin role'
    : isDriverBlocked
    ? 'Live capture disabled: Npcap driver is not installed or loaded.'
    : 'Start Capture Session';

  return (
    <div className="p-5 rounded-xl border border-white/10 bg-slate-900/70 backdrop-blur-md flex flex-col gap-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <Settings2 className="w-4 h-4 text-indigo-400" />
          <div>
            <h3 className="text-sm font-bold text-slate-100">Capture Session Controls</h3>
            {driverInfo?.available ? (
              <span className="text-[10px] text-emerald-400/90 font-mono flex items-center gap-1 mt-0.5">
                <CheckCircle2 className="w-3 h-3" />
                <span>Capture Driver Ready</span>
              </span>
            ) : driverInfo && !driverInfo.available ? (
              <span
                className="text-[10px] text-amber-400 font-mono flex items-center gap-1 mt-0.5"
                title={driverInfo.message || 'Npcap driver required for live capture'}
              >
                <AlertCircle className="w-3 h-3 text-amber-400" />
                <span>Driver Unavailable (Npcap Required)</span>
              </span>
            ) : null}
          </div>
        </div>

        {isRunning ? (
          <button
            onClick={handleStop}
            disabled={loading || !isAnalyst}
            title={!isAnalyst ? 'Action requires Analyst or Admin role' : 'Stop Capture Session'}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/25 transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : !isAnalyst ? <Lock className="w-4 h-4" /> : <Square className="w-4 h-4 fill-current" />}
            <span>Stop Capture</span>
          </button>
        ) : (
          <button
            onClick={handleStart}
            disabled={startDisabled}
            title={startTitle}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-white text-xs font-semibold shadow-lg transition disabled:opacity-50 ${
              isDriverBlocked
                ? 'bg-slate-700 cursor-not-allowed text-slate-400'
                : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/25'
            }`}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : !isAnalyst ? <Lock className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
            <span>Start Capture</span>
          </button>
        )}
      </div>

      {source === 'live' && driverInfo && !driverInfo.available && (
        <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/30 text-amber-200 text-xs flex flex-col gap-2">
          <div className="flex items-center gap-2 font-bold text-amber-300">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Npcap Packet Driver Required for Live Interface Sniffing</span>
          </div>
          <p className="text-amber-200/90 text-[11px] leading-relaxed">
            {driverInfo.message || 'Live network capture requires the Npcap kernel driver on Windows.'}
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1 border-t border-amber-500/20 text-[11px]">
            <a
              href="https://npcap.com/#download"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-amber-300 hover:text-white font-semibold underline underline-offset-2"
            >
              <span>Download Npcap Installer (npcap.com)</span>
              <span>&rarr;</span>
            </a>
            <span className="text-slate-400">•</span>
            <span className="text-slate-300">
              Select <strong>"Install Npcap in WinPcap API-compatible Mode"</strong> during installation.
            </span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Form Fields (disabled when running) */}
      <form onSubmit={handleStart} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        {/* Source Radio Toggle */}
        <div className="sm:col-span-2 lg:col-span-4 flex items-center gap-4">
          <span className="text-slate-400 font-semibold text-[11px] uppercase">Capture Source:</span>
          <label className="flex items-center gap-2 text-slate-200 cursor-pointer">
            <input
              type="radio"
              name="source"
              value="live"
              checked={source === 'live'}
              disabled={isRunning}
              onChange={(e) => setSource(e.target.value)}
              className="accent-indigo-500"
            />
            <Radio className="w-3.5 h-3.5 text-emerald-400" />
            <span>Live Interface Sniffer</span>
          </label>

          <label className="flex items-center gap-2 text-slate-200 cursor-pointer">
            <input
              type="radio"
              name="source"
              value="pcap"
              checked={source === 'pcap'}
              disabled={isRunning}
              onChange={(e) => setSource(e.target.value)}
              className="accent-indigo-500"
            />
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
            <span>Streaming PCAP Replay</span>
          </label>
        </div>

        {source === 'live' ? (
          <>
            <div className="sm:col-span-2">
              <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">
                Network Interface {interfaces.length > 0 && `(${interfaces.length} detected)`}
              </label>
              {interfaces.length > 0 ? (
                <select
                  disabled={isRunning}
                  value={interfaceName}
                  onChange={(e) => setInterfaceName(e.target.value)}
                  className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                >
                  <option value="">Auto-Detect Recommended Default</option>
                  {interfaces.map((iface, idx) => (
                    <option key={idx} value={iface.name}>
                      {iface.name} {iface.ip ? `(${iface.ip})` : ''} {iface.is_default ? '★ Recommended' : ''}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  disabled={isRunning}
                  value={interfaceName}
                  onChange={(e) => setInterfaceName(e.target.value)}
                  placeholder="Auto-Detect (e.g. Wi-Fi, Ethernet)"
                  className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
              )}
            </div>

            <div>
              <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">BPF Filter</label>
              <input
                type="text"
                disabled={isRunning}
                value={filterBpf}
                onChange={(e) => setFilterBpf(e.target.value)}
                placeholder="tcp or udp"
                className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
              />
            </div>
          </>
        ) : (
          <>
            <div className="sm:col-span-2">
              <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">PCAP File Path</label>
              <input
                type="text"
                disabled={isRunning}
                value={pcapFile}
                onChange={(e) => setPcapFile(e.target.value)}
                placeholder="data/sample/sample_network_traffic.pcap"
                className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">Replay Speed Factor</label>
              <select
                disabled={isRunning}
                value={replaySpeed}
                onChange={(e) => setReplaySpeed(Number(e.target.value))}
                className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
              >
                <option value={0.0}>0.0 (Max Throughput)</option>
                <option value={1.0}>1.0x (Real-time Pacing)</option>
                <option value={2.0}>2.0x (Double Speed)</option>
                <option value={5.0}>5.0x (5x Speed)</option>
              </select>
            </div>
          </>
        )}

        <div>
          <label className="block text-slate-400 text-[10px] font-bold uppercase mb-1">Packet Limit</label>
          <input
            type="number"
            disabled={isRunning}
            min={10}
            max={1000000}
            value={maxPackets}
            onChange={(e) => setMaxPackets(Number(e.target.value))}
            className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 font-mono text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
          />
        </div>
      </form>
    </div>
  );
}

export default MonitoringControls;

