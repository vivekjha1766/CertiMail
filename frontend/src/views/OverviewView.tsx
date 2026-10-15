import React from 'react';
import {
  Users,
  CheckCircle,
  FileCheck2,
  MailCheck,
  Send,
  AlertOctagon,
  Clock,
  ArrowRight,
  UploadCloud,
  FileSpreadsheet,
  Settings,
  Sparkles,
  ShieldCheck
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export const OverviewView: React.FC = () => {
  const { validationReport, overviewStats, setActiveView, excelData, batches } = useApp();

  const totalLoaded = validationReport?.summary.total_teams || excelData?.row_count || 0;
  const validTeams = validationReport?.summary.valid_teams || 0;
  const certsDetected = validationReport?.summary.total_certificates_detected || batches.reduce((acc, b) => acc + b.file_count, 0);
  const readyToSend = validationReport?.summary.can_send ? validTeams : 0;
  
  const sentCount = overviewStats?.total_sent || 0;
  const failedCount = overviewStats?.total_failed || 0;
  const pendingCount = overviewStats?.pending || 0;

  const statCards = [
    {
      label: 'Total Teams Loaded',
      value: totalLoaded,
      subtext: excelData ? `${excelData.filename}` : 'No workbook loaded',
      icon: Users,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      border: 'border-blue-100'
    },
    {
      label: 'Valid Teams',
      value: validTeams,
      subtext: validationReport ? `${Math.round((validTeams / (totalLoaded || 1)) * 100)}% passing` : 'Pending validation',
      icon: CheckCircle,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      border: 'border-emerald-100'
    },
    {
      label: 'Certificates Detected',
      value: certsDetected,
      subtext: `${batches.length} of 6 batches uploaded`,
      icon: FileCheck2,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
      border: 'border-indigo-100'
    },
    {
      label: 'Emails Ready to Send',
      value: readyToSend,
      subtext: readyToSend > 0 ? 'Approved for dispatch' : 'Blocked until valid',
      icon: MailCheck,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      border: 'border-purple-100'
    },
    {
      label: 'Sent Successfully',
      value: sentCount,
      subtext: 'SMTP accepted',
      icon: Send,
      color: 'text-teal-600',
      bg: 'bg-teal-50',
      border: 'border-teal-100'
    },
    {
      label: 'Failed Emails',
      value: failedCount,
      subtext: failedCount > 0 ? 'Requires attention' : 'Zero failures',
      icon: AlertOctagon,
      color: 'text-rose-600',
      bg: 'bg-rose-50',
      border: 'border-rose-100'
    },
    {
      label: 'Emails Pending',
      value: pendingCount,
      subtext: 'Awaiting delivery',
      icon: Clock,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-100'
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-8 shadow-xl">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            Hack-O-Sprint 4.0 • Certificate Distribution Dashboard
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Automate Personalized Team Certificate Mailing
          </h2>
          <p className="text-slate-300 text-sm leading-relaxed">
            Eliminate manual certificate sorting and repetitive email sending. Match each 6-member team with its 6 unique certificates from bulk ZIP archives and deliver them securely via SMTP with STARTTLS.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveView('upload')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs tracking-wide transition-all shadow-md"
            >
              <UploadCloud className="w-4 h-4" />
              Upload Excel & ZIP Archives
            </button>
            <button
              onClick={() => setActiveView('settings')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 font-semibold text-xs tracking-wide transition-all border border-slate-700"
            >
              <Settings className="w-4 h-4" />
              Configure SMTP Settings
            </button>
          </div>
        </div>
      </div>

      {/* Main KPI Stat Grid */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
          Distribution Metrics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card, i) => {
            const Icon = card.icon;
            return (
              <div
                key={i}
                className={`bg-white p-5 rounded-xl border ${card.border} shadow-xs hover:shadow-md transition-shadow`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500">{card.label}</span>
                  <div className={`p-2 rounded-lg ${card.bg} ${card.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <div className="mt-3">
                  <div className="text-2xl font-black text-slate-900 tracking-tight">{card.value}</div>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{card.subtext}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Workflow Stepper */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <h3 className="text-base font-bold text-slate-900 mb-4">Standard Operational Workflow</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div
            onClick={() => setActiveView('upload')}
            className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
              1
            </div>
            <h4 className="text-sm font-bold text-slate-800">Upload Files</h4>
            <p className="text-xs text-slate-500 mt-1">
              Select Excel sheet and upload 6 participant position ZIP archives.
            </p>
          </div>

          <div
            onClick={() => setActiveView('mapping')}
            className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
              2
            </div>
            <h4 className="text-sm font-bold text-slate-800">Verify Mapping</h4>
            <p className="text-xs text-slate-500 mt-1">
              Inspect 1:1 certificate matches, check references, and resolve errors.
            </p>
          </div>

          <div
            onClick={() => setActiveView('preview_test')}
            className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
              3
            </div>
            <h4 className="text-sm font-bold text-slate-800">Preview & Test Send</h4>
            <p className="text-xs text-slate-500 mt-1">
              Check real certificate PNG thumbnails and send a safe test email to yourself.
            </p>
          </div>

          <div
            onClick={() => setActiveView('send')}
            className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
              4
            </div>
            <h4 className="text-sm font-bold text-slate-800">Execute Campaign</h4>
            <p className="text-xs text-slate-500 mt-1">
              Start sequential bulk sending with live progress, pause/resume, and logging.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
