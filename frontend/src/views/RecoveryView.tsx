import React, { useState, useEffect } from 'react';
import {
  RotateCcw,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Mail,
  HelpCircle,
  XCircle,
  FileText,
  Layers,
  ArrowRight,
  RefreshCw,
  Search,
  Filter
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient, CampaignRecoveryItem } from '../api/client';

export const RecoveryView: React.FC = () => {
  const { setActiveCampaignId, setActiveView, addToast } = useApp();

  const [campaigns, setCampaigns] = useState<CampaignRecoveryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadRecoverableCampaigns();
  }, []);

  const loadRecoverableCampaigns = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getRecoverableCampaigns();
      setCampaigns(data);
    } catch (e: any) {
      addToast('error', 'Recovery Load Failed', e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInspectCampaign = (cId: string) => {
    setActiveCampaignId(cId);
    setActiveView('send');
    addToast('info', 'Campaign Selected', `Loaded campaign ${cId.slice(0, 8)}... into inspection & continuation console.`);
  };

  const filteredCampaigns = campaigns.filter((c) => {
    const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) || c.id.toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;

    if (filterType === 'resumable') return c.is_resumable;
    if (filterType === 'paused') return c.status === 'paused';
    if (filterType === 'interrupted') return c.status === 'interrupted';
    if (filterType === 'uncertain') return c.uncertain_count > 0;
    if (filterType === 'completed') return c.status === 'completed';
    return true;
  });

  const getStatusBadge = (status: string, uncertainCount: number) => {
    if (uncertainCount > 0) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
          <HelpCircle className="w-3 h-3" />
          {uncertainCount} Uncertain
        </span>
      );
    }
    switch (status) {
      case 'sending':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" />
            Sending
          </span>
        );
      case 'paused':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            <Pause className="w-3 h-3" />
            Paused
          </span>
        );
      case 'interrupted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            <AlertTriangle className="w-3 h-3" />
            Interrupted
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3 h-3" />
            Completed
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            <XCircle className="w-3 h-3" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <RotateCcw className="w-5 h-5 text-indigo-600" />
            Campaign Recovery & Session Continuation
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Safely resume interrupted mailings, resolve delivery uncertainties, or inspect completed distribution manifests across application restarts.
          </p>
        </div>

        <button
          onClick={loadRecoverableCampaigns}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Registry
        </button>
      </div>

      {/* Safety Notice Card */}
      <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-2xl flex items-start gap-3.5 text-xs text-indigo-950 leading-relaxed">
        <Clock className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold block mb-0.5">Safe Continuation Guarantee</strong>
          CertiMail persists delivery states in SQLite. When you resume a campaign, recipients already marked <code className="font-mono bg-white px-1 py-0.5 rounded border border-indigo-200 text-emerald-800 font-bold">SMTP_ACCEPTED</code> will <strong>never</strong> be resent. Uncertain transmissions (<code className="font-mono bg-white px-1 py-0.5 rounded border border-indigo-200 text-amber-800 font-bold">DELIVERY_UNKNOWN</code>) require explicit review before dispatch to eliminate duplicate emails.
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search campaigns by name or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-700 focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Campaigns ({campaigns.length})</option>
            <option value="resumable">Resumable Only</option>
            <option value="paused">Paused</option>
            <option value="interrupted">Interrupted / Recovered</option>
            <option value="uncertain">With Uncertain Deliveries</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      {/* Campaigns Recovery Cards Grid */}
      {filteredCampaigns.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-3">
          <Layers className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-base font-bold text-slate-800">No campaigns match your filter</h3>
          <p className="text-xs text-slate-500">
            Create and run a campaign in Step 6 to see it registered here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCampaigns.map((camp) => (
            <div
              key={camp.id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs hover:border-indigo-200 hover:shadow-sm transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] font-mono uppercase text-slate-400 block tracking-wider truncate">
                      ID: {camp.id}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 truncate mt-0.5" title={camp.name}>
                      {camp.name}
                    </h3>
                  </div>
                  <div>{getStatusBadge(camp.status, camp.uncertain_count)}</div>
                </div>

                <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Last Activity: {new Date(camp.last_activity).toLocaleString()}</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2 text-xs">
                  <div className="flex justify-between items-center text-slate-600 font-medium">
                    <span>Campaign Type:</span>
                    <span className="capitalize font-semibold text-slate-800">{camp.campaign_type.replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600 font-medium">
                    <span>Active Template Revision:</span>
                    <span className="font-bold text-indigo-600">Rev {camp.current_template_revision}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600 font-medium">
                    <span>Accepted Deliveries:</span>
                    <span className="font-bold text-emerald-600">{camp.accepted_count} / {camp.total_recipients}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600 font-medium">
                    <span>Remaining to Send:</span>
                    <span className="font-bold text-indigo-600">{camp.remaining_count}</span>
                  </div>
                  {camp.uncertain_count > 0 && (
                    <div className="flex justify-between items-center text-amber-700 font-medium bg-amber-50/80 px-2 py-1 rounded">
                      <span>Uncertain (Pending Review):</span>
                      <span className="font-bold">{camp.uncertain_count}</span>
                    </div>
                  )}
                  {camp.failed_count > 0 && (
                    <div className="flex justify-between items-center text-rose-700 font-medium bg-rose-50/80 px-2 py-1 rounded">
                      <span>Failed Deliveries:</span>
                      <span className="font-bold">{camp.failed_count}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400">
                  {camp.is_resumable ? 'Ready to resume' : 'Review only'}
                </span>

                <button
                  onClick={() => handleInspectCampaign(camp.id)}
                  className={`inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl transition-colors shadow-2xs ${
                    camp.is_resumable
                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  <span>{camp.is_resumable ? 'Inspect & Resume' : 'View Ledger'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
