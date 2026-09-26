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

  const inputClasses = "w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg px-3 py-2.5 text-[#0F172A] text-xs font-medium focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]/30 disabled:opacity-50 transition";
  const selectClasses = "w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg px-3 py-2.5 text-[#0F172A] text-xs font-medium focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]/30 disabled:opacity-50 transition";
  const labelClasses = "block text-[#64748B] text-[10px] font-bold uppercase tracking-wider mb-1.5";

  return (
    <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white shadow-sm flex flex-col gap-4 hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#EAF2FF] border border-[#2563EB]/20 text-[#2563EB]">
            <Settings2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#0F172A]">Capture Session Controls</h3>
            {driverInfo?.available ? (
              <span className="text-[10px] text-[#10B981] font-mono flex items-center gap-1 mt-0.5">
                <CheckCircle2 className="w-3 h-3" />
                <span>Capture Driver Ready</span>
              </span>
            ) : driverInfo && !driverInfo.available ? (
              <span
                className="text-[10px] text-[#F59E0B] font-mono flex items-center gap-1 mt-0.5"
                title={driverInfo.message || 'Npcap driver required for live capture'}
              >
                <AlertCircle className="w-3 h-3 text-[#F59E0B]" />
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
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#EF4444] hover:bg-red-600 text-white text-xs font-bold shadow-md shadow-red-500/25 transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : !isAnalyst ? <Lock className="w-4 h-4" /> : <Square className="w-4 h-4 fill-current" />}
            <span>Stop Capture</span>
          </button>
        ) : (
          <button
            onClick={handleStart}
            disabled={startDisabled}
            title={startTitle}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold shadow-md transition disabled:opacity-50 ${
              isDriverBlocked
                ? 'bg-slate-200 cursor-not-allowed text-[#64748B]'
                : 'bg-[#10B981] hover:bg-emerald-600 text-white shadow-emerald-500/25'
            }`}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : !isAnalyst ? <Lock className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
            <span>Start Capture</span>
          </button>
        )}
      </div>

      {source === 'live' && driverInfo && !driverInfo.available && (
        <div className="p-3.5 rounded-xl bg-[#FFFBEB] border border-[#F59E0B]/30 text-[#92400E] text-xs flex flex-col gap-2">
          <div className="flex items-center gap-2 font-bold text-[#B45309]">
            <AlertCircle className="w-4 h-4 text-[#F59E0B] shrink-0" />
            <span>Npcap Packet Driver Required for Live Interface Sniffing</span>
          </div>
          <p className="text-[#78350F] text-[11px] leading-relaxed">
            {driverInfo.message || 'Live network capture requires the Npcap kernel driver on Windows.'}
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1 border-t border-[#F59E0B]/20 text-[11px]">
            <a
              href="https://npcap.com/#download"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[#2563EB] hover:text-[#1D4ED8] font-semibold underline underline-offset-2"
            >
              <span>Download Npcap Installer (npcap.com)</span>
              <span>&rarr;</span>
            </a>
            <span className="text-[#CBD5E1]">•</span>
            <span className="text-[#64748B]">
              Select <strong>"Install Npcap in WinPcap API-compatible Mode"</strong> during installation.
            </span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-[#EF4444]/30 text-[#991B1B] text-xs">
          {error}
        </div>
      )}

      {/* Form Fields (disabled when running) */}
      <form onSubmit={handleStart} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        {/* Source Radio Toggle */}
        <div className="sm:col-span-2 lg:col-span-4 flex items-center gap-4">
          <span className="text-[#64748B] font-semibold text-[11px] uppercase">Capture Source:</span>
          <label className="flex items-center gap-2 text-[#0F172A] cursor-pointer">
            <input
              type="radio"
              name="source"
              value="live"
              checked={source === 'live'}
              disabled={isRunning}
              onChange={(e) => setSource(e.target.value)}
              className="accent-[#2563EB]"
            />
            <Radio className="w-3.5 h-3.5 text-[#10B981]" />
            <span className="font-medium">Live Interface Sniffer</span>
          </label>

          <label className="flex items-center gap-2 text-[#0F172A] cursor-pointer">
            <input
              type="radio"
              name="source"
              value="pcap"
              checked={source === 'pcap'}
              disabled={isRunning}
              onChange={(e) => setSource(e.target.value)}
              className="accent-[#2563EB]"
            />
            <FileText className="w-3.5 h-3.5 text-[#4F46E5]" />
            <span className="font-medium">Streaming PCAP Replay</span>
          </label>
        </div>

        {source === 'live' ? (
          <>
            <div className="sm:col-span-2">
              <label className={labelClasses}>
                Network Interface {interfaces.length > 0 && `(${interfaces.length} detected)`}
              </label>
              {interfaces.length > 0 ? (
                <select
                  disabled={isRunning}
                  value={interfaceName}
                  onChange={(e) => setInterfaceName(e.target.value)}
                  className={selectClasses}
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
                  className={`${inputClasses} font-mono`}
                />
              )}
            </div>

            <div>
              <label className={labelClasses}>BPF Filter</label>
              <input
                type="text"
                disabled={isRunning}
                value={filterBpf}
                onChange={(e) => setFilterBpf(e.target.value)}
                placeholder="tcp or udp"
                className={`${inputClasses} font-mono`}
              />
            </div>
          </>
        ) : (
          <>
            <div className="sm:col-span-2">
              <label className={labelClasses}>PCAP File Path</label>
              <input
                type="text"
                disabled={isRunning}
                value={pcapFile}
                onChange={(e) => setPcapFile(e.target.value)}
                placeholder="data/sample/sample_network_traffic.pcap"
                className={`${inputClasses} font-mono`}
              />
            </div>

            <div>
              <label className={labelClasses}>Replay Speed Factor</label>
              <select
                disabled={isRunning}
                value={replaySpeed}
                onChange={(e) => setReplaySpeed(Number(e.target.value))}
                className={selectClasses}
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
          <label className={labelClasses}>Packet Limit</label>
          <input
            type="number"
            disabled={isRunning}
            min={10}
            max={1000000}
            value={maxPackets}
            onChange={(e) => setMaxPackets(Number(e.target.value))}
            className={`${inputClasses} font-mono`}
          />
        </div>
      </form>
    </div>
  );
}

export default MonitoringControls;

