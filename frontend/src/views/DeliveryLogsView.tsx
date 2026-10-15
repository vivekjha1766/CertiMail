import React, { useState, useEffect } from 'react';
import {
  ScrollText,
  Download,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Clock,
  Paperclip,
  ShieldCheck
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient, DeliveryLogItem } from '../api/client';

export const DeliveryLogsView: React.FC = () => {
  const { activeCampaignId } = useApp();

  const [logs, setLogs] = useState<DeliveryLogItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SENT' | 'FAILED'>('ALL');

  useEffect(() => {
    fetchLogs();
  }, [activeCampaignId, statusFilter]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await apiClient.getDeliveryLogs({
        campaign_id: activeCampaignId || undefined,
        status: statusFilter,
        search: searchTerm || undefined,
        limit: 150
      });
      setLogs(data.items);
      setTotalCount(data.total);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLogs();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Step 7: Delivery Logs & Audit History</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Immutable audit record of all email delivery attempts, attachment counts, and SMTP responses.
          </p>
        </div>

        {/* CSV Export Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <a
            href={apiClient.getExportLogsUrl('all', activeCampaignId || undefined)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-2xs transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            Export All
          </a>
          <a
            href={apiClient.getExportLogsUrl('sent', activeCampaignId || undefined)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 text-emerald-800 text-xs font-semibold rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-emerald-600" />
            Export Sent
          </a>
          <a
            href={apiClient.getExportLogsUrl('failed', activeCampaignId || undefined)}
            download
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 border border-rose-200 hover:bg-rose-100 text-rose-800 text-xs font-semibold rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-rose-600" />
            Export Failed
          </a>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg transition-colors"
            title="Refresh logs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by team or recipient email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
          />
        </div>

        <div className="flex items-center gap-1.5 self-end sm:self-auto">
          <button
            type="button"
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'ALL'
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Logs ({totalCount})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('SENT')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'SENT'
                ? 'bg-emerald-600 text-white'
                : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            }`}
          >
            Sent Only
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter('FAILED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'FAILED'
                ? 'bg-rose-600 text-white'
                : 'bg-rose-50 text-rose-700 hover:bg-rose-100'
            }`}
          >
            Failed Only
          </button>
        </div>
      </form>

      {/* Delivery Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 font-bold text-slate-600 uppercase tracking-wider">
                <th className="py-3 px-4 w-36">Timestamp</th>
                <th className="py-3 px-4 min-w-[160px]">Team Name</th>
                <th className="py-3 px-4 min-w-[180px]">Recipient Email</th>
                <th className="py-3 px-4 w-28">CC / BCC</th>
                <th className="py-3 px-4 w-28 text-center">Attachments</th>
                <th className="py-3 px-4 w-28 text-center">Status</th>
                <th className="py-3 px-4 min-w-[200px]">Notes / Error Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No delivery log entries recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                      {log.created_at.substring(0, 19).replace('T', ' ')}
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-800">
                      {log.team_name || 'N/A'}
                      {log.is_test && (
                        <span className="ml-2 text-[10px] font-semibold uppercase px-1.5 py-0.2 bg-amber-100 text-amber-800 rounded">
                          Test
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700 truncate max-w-[200px]" title={log.recipient_email}>
                      {log.recipient_email}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      <div>CC: {log.cc_recipients ? log.cc_recipients.split(',').length : 0}</div>
                      <div className="text-[10px] text-slate-400">BCC: {log.bcc_count} hidden</div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex items-center gap-1 font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                        <Paperclip className="w-3 h-3 text-slate-500" />
                        {log.attachment_count}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {log.status === 'SENT' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" />
                          SENT
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                          <XCircle className="w-3 h-3" />
                          FAILED
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {log.error_message ? (
                        <span className="text-rose-600 font-sans" title={log.error_message}>
                          {log.error_message.substring(0, 80)}...
                        </span>
                      ) : (
                        <span className="text-emerald-700 text-[11px]">SMTP Accepted for delivery</span>
                      )}
                      {log.retry_count > 0 && (
                        <span className="text-[10px] text-slate-400 block">Retried: {log.retry_count} time(s)</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
