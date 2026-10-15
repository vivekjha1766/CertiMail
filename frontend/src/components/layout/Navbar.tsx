import React from 'react';
import { Mail, Award, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const Navbar: React.FC = () => {
  const { validationReport, sessionId, setActiveView } = useApp();

  const renderStatusBadge = () => {
    if (!validationReport) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
          <span className="w-2 h-2 rounded-full bg-slate-400"></span>
          No Data Loaded
        </span>
      );
    }

    const { summary } = validationReport;
    if (summary.can_send) {
      return (
        <button
          onClick={() => setActiveView('mapping')}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors"
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          VALIDATION PASSED ({summary.valid_teams} / {summary.total_teams} TEAMS)
        </button>
      );
    }

    return (
      <button
        onClick={() => setActiveView('mapping')}
        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition-colors"
      >
        <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
        {summary.error_teams} TEAMS REQUIRE REVIEW
      </button>
    );
  };

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-xs">
      <div className="px-6 py-3.5 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-indigo-100">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">CertiMail</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-100">
                v1.0 Local
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">Certificate Distribution Dashboard & Automation</p>
          </div>
        </div>

        {/* Status Center */}
        <div className="flex items-center gap-4">
          {renderStatusBadge()}

          <div className="hidden md:flex items-center gap-2 pl-4 border-l border-slate-200">
            <ShieldCheck className="w-4 h-4 text-slate-400" />
            <span className="text-xs text-slate-500">Session:</span>
            <code className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-700 border border-slate-200">
              {sessionId.substring(0, 16)}...
            </code>
          </div>
        </div>
      </div>
    </header>
  );
};
