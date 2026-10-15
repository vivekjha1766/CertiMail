import React, { useState } from 'react';
import {
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Edit,
  Eye,
  Search,
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  HelpCircle,
  RotateCcw
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { TeamMappingItem, CertificateFileInfo, apiClient } from '../api/client';
import { ImageLightboxModal } from '../components/modals/ImageLightboxModal';
import { ManualOverrideModal } from '../components/modals/ManualOverrideModal';
import { ProceedMappingModal } from '../components/modals/ProceedMappingModal';

export const MappingView: React.FC = () => {
  const { validationReport, setValidationReport, sessionId, setActiveView, addToast } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'VALID' | 'OVERRIDES' | 'ERRORS'>('ALL');
  
  // Modals state
  const [selectedCertForModal, setSelectedCertForModal] = useState<CertificateFileInfo | null>(null);
  const [selectedTeamForOverride, setSelectedTeamForOverride] = useState<TeamMappingItem | null>(null);
  const [isProceedModalOpen, setIsProceedModalOpen] = useState(false);
  const [resettingAck, setResettingAck] = useState(false);

  if (!validationReport) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-xl flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">No Mapping Data Available</h3>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          Please upload your Excel teams list and 6 certificate ZIP files in Step 2 to generate the validation mapping.
        </p>
        <button
          onClick={() => setActiveView('upload')}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors"
        >
          Go to Step 2: Upload Files
        </button>
      </div>
    );
  }

  const { summary, teams } = validationReport;

  // Filtered teams list
  const filteredTeams = teams.filter((t) => {
    const matchesSearch =
      t.team_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.leader_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.leader_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.team_identifier?.toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === 'VALID') return t.validation_status === 'VALID';
    if (statusFilter === 'OVERRIDES') return t.validation_status === 'OVERRIDE_APPROVED';
    if (statusFilter === 'ERRORS') return t.validation_status !== 'VALID' && t.validation_status !== 'OVERRIDE_APPROVED';
    return true;
  });

  const getStatusBadge = (status: string, override: boolean) => {
    if (status === 'OVERRIDE_APPROVED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
          OVERRIDE APPROVED
        </span>
      );
    }
    if (status === 'VALID') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3 h-3" />
          VALID
        </span>
      );
    }
    if (status === 'REFERENCE_MISMATCH') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-300">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
          REFERENCE MISMATCH
        </span>
      );
    }
    if (status === 'OVERRIDE_REVOKED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-300">
          <RotateCcw className="w-3 h-3 text-amber-600" />
          OVERRIDE REVOKED
        </span>
      );
    }
    if (status === 'OVERRIDE_REJECTED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-800 border border-rose-300">
          <XCircle className="w-3 h-3 text-rose-600" />
          OVERRIDE REJECTED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
        <XCircle className="w-3 h-3" />
        {status}
      </span>
    );
  };

  const directlyValidCount = teams.filter((t) => t.validation_status === 'VALID').length;
  const approvedOverridesCount = teams.filter((t) => t.validation_status === 'OVERRIDE_APPROVED').length;
  const mismatchedTeams = teams.filter((t) => t.validation_status === 'REFERENCE_MISMATCH');
  const isOptionAAuthorized = Boolean(summary.mismatch_acknowledgement);

  const handleResetAcknowledgement = async () => {
    if (!confirm('Revoke Option A authorization and return to manual individual review mode?')) return;
    setResettingAck(true);
    try {
      const updated = await apiClient.resetMismatchAcknowledgement(sessionId);
      setValidationReport(updated);
      addToast('info', 'Authorization Revoked', 'Returned to manual individual review mode.');
    } catch (err: any) {
      addToast('error', 'Reset Failed', err.response?.data?.detail || err.message);
    } finally {
      setResettingAck(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Step 3: Certificate Mapping & Approval Audit</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Audit 1:1 certificate matches for all {summary.total_teams} teams. Explicitly review and authorize overrides before initiating bulk distribution.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={apiClient.getReportDownloadUrl(sessionId)}
            download
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl shadow-2xs transition-colors"
          >
            <Download className="w-4 h-4 text-slate-500" />
            Download Audit CSV
          </a>

          {summary.can_send ? (
            <button
              onClick={() => setActiveView('composer')}
              className="inline-flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
            >
              Proceed to Composer
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              disabled
              title="All mapping errors must be resolved or explicitly approved before sending"
              className="inline-flex items-center gap-2 px-5 py-2 bg-slate-300 text-slate-500 text-xs font-semibold rounded-xl cursor-not-allowed"
            >
              Resolve Errors or Authorize ({summary.error_teams} Remaining)
            </button>
          )}
        </div>
      </div>

      {/* Validation Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] text-slate-500 font-medium">Total Teams</span>
          <div className="text-xl font-bold text-slate-900 mt-0.5">{summary.total_teams}</div>
          <span className="text-[10px] text-slate-400">72 team target</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] text-slate-500 font-medium">Direct Valid Teams</span>
          <div className="text-xl font-bold text-emerald-600 mt-0.5">{directlyValidCount}</div>
          <span className="text-[10px] text-emerald-600 font-medium">Auto-matched</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] text-slate-500 font-medium">Approved Overrides</span>
          <div className="text-xl font-bold text-indigo-600 mt-0.5">{approvedOverridesCount}</div>
          <span className="text-[10px] text-indigo-600 font-medium">Audited & authorized</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[11px] text-slate-500 font-medium">Unresolved Issues</span>
          <div className={`text-xl font-bold mt-0.5 ${summary.error_teams > 0 ? 'text-rose-600' : 'text-slate-400'}`}>
            {summary.error_teams}
          </div>
          <span className="text-[10px] text-slate-400">
            {summary.reference_mismatches > 0 ? `${summary.reference_mismatches} ref mismatch` : 'Must be 0'}
          </span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs col-span-2 sm:col-span-1">
          <span className="text-[11px] text-slate-500 font-medium flex items-center gap-1">
            Bulk Send Barrier
            <span title="Campaign cannot be created or sent while any team has unresolved validation issues.">
              <HelpCircle className="w-3 h-3 text-slate-400" />
            </span>
          </span>
          <div className="mt-1">
            {summary.can_send ? (
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1 w-fit">
                <CheckCircle2 className="w-3 h-3" />
                {isOptionAAuthorized ? 'OPTION A UNLOCKED' : 'UNLOCKED'}
              </span>
            ) : (
              <span className="text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 flex items-center gap-1 w-fit">
                <ShieldAlert className="w-3 h-3" />
                LOCKED ({summary.error_teams})
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Active Option A Authorization Banner */}
      {isOptionAAuthorized && summary.mismatch_acknowledgement && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-emerald-950 text-sm">Option A Active: Proceeding with Current Mapping</span>
                <span className="text-[10px] bg-emerald-200/80 text-emerald-900 px-2 py-0.5 rounded-full font-bold">Authorized</span>
              </div>
              <p className="text-xs text-emerald-800 mt-0.5">
                Authorized by <strong>{summary.mismatch_acknowledgement.reviewer}</strong>: "{summary.mismatch_acknowledgement.reason}". {summary.reference_mismatches} reference mismatch(es) waived for campaign dispatch while preserved in the audit log.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleResetAcknowledgement}
              disabled={resettingAck}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl transition-colors shadow-2xs"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              {resettingAck ? 'Reverting...' : 'Switch to Option B (Manual Review)'}
            </button>
            <button
              onClick={() => setActiveView('composer')}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-xs transition-colors"
            >
              Proceed to Composer
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Option A vs Option B Workflow Decision Card (when mismatches exist and not yet authorized) */}
      {!isOptionAAuthorized && summary.reference_mismatches > 0 && (
        <div className="bg-white rounded-2xl border border-indigo-100 shadow-xs p-5 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 text-[11px] font-bold tracking-wider uppercase rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Workflow Decision
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  Certificate Review Policy: Choose How to Proceed
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-1 max-w-3xl leading-relaxed">
                The mapper assigned certificates for all {summary.total_teams} teams, but detected {summary.reference_mismatches} reference sequence mismatch(es). You can either proceed directly using the existing certificate mapping with an audit confirmation (Option A), or manually review and edit individual teams (Option B).
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            {/* Option A Card */}
            <div className="p-4 rounded-xl border border-indigo-200 bg-indigo-50/40 hover:bg-indigo-50/60 transition-all flex flex-col justify-between space-y-3">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-indigo-950 text-sm flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-600" />
                    Option A — Proceed with Current Mapping
                  </span>
                  <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded-full">
                    Recommended for minor offset
                  </span>
                </div>
                <p className="text-xs text-indigo-900/80 leading-relaxed">
                  Continue using the current certificate assignments produced by the existing mapper. Does <strong>not require</strong> manual approval or override for every team individually. Requires explicit audit confirmation.
                </p>
                <ul className="text-[11px] text-indigo-950 space-y-1 pt-1 font-medium">
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                    Preserves all mapped certificates and member assignments as-is
                  </li>
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                    Full audit trail: records reviewer identity, timestamp & mismatch summary
                  </li>
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                    Hard safety gate: Missing files or bad emails still strictly blocked
                  </li>
                </ul>
              </div>
              <button
                onClick={() => setIsProceedModalOpen(true)}
                className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center gap-2"
              >
                Proceed with Current Mapping (Option A)
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Option B Card */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 hover:bg-slate-50 transition-all flex flex-col justify-between space-y-3">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <Edit className="w-4 h-4 text-slate-600" />
                    Option B — Review and Edit Mapping
                  </span>
                  <span className="text-[10px] font-semibold text-slate-600 bg-slate-200/60 px-2 py-0.5 rounded-full">
                    Manual inspection
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Retain the granular manual review workflow. Inspect individual teams, edit assignments, and approve, reject, or revoke overrides with persistent hash protection.
                </p>
                <ul className="text-[11px] text-slate-600 space-y-1 pt-1 font-medium">
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    Inspect and override specific teams one by one
                  </li>
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    Unaffected teams ({directlyValidCount}) require no manual review
                  </li>
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    Automated hash invalidation if underlying assignments change
                  </li>
                </ul>
              </div>
              <button
                onClick={() => {
                  setStatusFilter('ERRORS');
                  const el = document.getElementById('audit-table-section');
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
                className="w-full py-2 px-4 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold text-xs rounded-xl shadow-2xs transition-colors flex items-center justify-center gap-2"
              >
                Review Individual Teams (Option B)
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Security Gate Alert if errors present and not authorized */}
      {!summary.can_send && (summary.has_fatal_errors || summary.missing_certificates > 0 || summary.duplicate_emails > 0) && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-900 leading-relaxed">
            <strong className="font-semibold block mb-0.5">Strict Validation Gate Active: Fatal Errors Present</strong>
            Bulk sending is strictly blocked because <strong>{summary.error_teams} team(s)</strong> have errors, including missing certificates or recipient errors. These cannot be waived by Option A and must be resolved before sending.
          </div>
        </div>
      )}


      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search team, leader name, email, or team ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
          />
        </div>

        <div className="flex items-center gap-1.5 self-end sm:self-auto flex-wrap">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'ALL'
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All ({teams.length})
          </button>
          <button
            onClick={() => setStatusFilter('VALID')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'VALID'
                ? 'bg-emerald-600 text-white'
                : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            }`}
          >
            Valid ({directlyValidCount})
          </button>
          <button
            onClick={() => setStatusFilter('OVERRIDES')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'OVERRIDES'
                ? 'bg-indigo-600 text-white'
                : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
            }`}
          >
            Approved Overrides ({approvedOverridesCount})
          </button>
          <button
            onClick={() => setStatusFilter('ERRORS')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              statusFilter === 'ERRORS'
                ? 'bg-rose-600 text-white'
                : 'bg-rose-50 text-rose-700 hover:bg-rose-100'
            }`}
          >
            Issues Requiring Review ({summary.error_teams})
          </button>
        </div>
      </div>

      {/* Audit Table */}
      <div id="audit-table-section" className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 font-bold text-slate-600 uppercase tracking-wider">
                <th className="py-3 px-4 w-12 text-center">Row</th>
                <th className="py-3 px-4 min-w-[180px]">Team & Leader</th>
                <th className="py-3 px-4 min-w-[200px]">Leader Email (To:)</th>
                <th className="py-3 px-4 min-w-[340px]">6 Certificate Attachments (Positions 1 to 6)</th>
                <th className="py-3 px-4 w-40">Validation Status</th>
                <th className="py-3 px-4 w-24 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {filteredTeams.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No teams found matching your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredTeams.map((team) => {
                  const isApprovedOverride = team.validation_status === 'OVERRIDE_APPROVED';
                  const isRefMismatch = team.validation_status === 'REFERENCE_MISMATCH';
                  const isRevoked = team.validation_status === 'OVERRIDE_REVOKED';

                  return (
                    <tr
                      key={team.team_id}
                      className={`hover:bg-slate-50/70 transition-colors ${
                        isApprovedOverride
                          ? 'bg-indigo-50/15'
                          : team.validation_status !== 'VALID'
                          ? 'bg-rose-50/20'
                          : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-center font-mono text-slate-400">
                        {team.row_index}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-800 flex items-center gap-1.5">
                          {team.team_name}
                          {team.team_identifier && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-100 text-slate-600">
                              {team.team_identifier}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Lead: <span className="text-slate-700">{team.leader_name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-mono text-slate-700 truncate max-w-[220px]" title={team.leader_email}>
                          {team.leader_email}
                        </div>
                        {team.cc_recipients && (
                          <div className="text-[10px] text-slate-400 truncate max-w-[220px]" title={team.cc_recipients}>
                            CC: {team.cc_recipients}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {team.certificate_files.map((cert) => (
                            <button
                              key={cert.position}
                              onClick={() => setSelectedCertForModal(cert)}
                              title={`Pos ${cert.position}: ${cert.participant_name || 'Member'} (${cert.filename}) - Click to preview lightbox`}
                              className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-mono border transition-all ${
                                cert.exists
                                  ? 'bg-slate-50 text-slate-700 border-slate-200 hover:border-indigo-400 hover:bg-indigo-50'
                                  : 'bg-rose-100 text-rose-800 border-rose-300 font-bold animate-pulse'
                              }`}
                            >
                              <span>P{cert.position}:</span>
                              <span className="truncate max-w-[70px]">{cert.filename}</span>
                              <Eye className="w-3 h-3 text-slate-400 ml-0.5" />
                            </button>
                          ))}
                        </div>

                        {/* Audit Details */}
                        {isApprovedOverride && (
                          <div className="mt-1.5 text-[11px] text-indigo-800 bg-indigo-50/80 border border-indigo-200 rounded-lg px-2.5 py-1 flex items-start gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
                            <div className="leading-tight">
                              <span>
                                Approved by <strong>{team.override_reviewer || 'Admin'}</strong>
                              </span>
                              {team.override_reason && (
                                <span className="text-indigo-900 block mt-0.5">
                                  "{team.override_reason}"
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {isRefMismatch && (
                          <div className="mt-1.5 text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1 flex items-start gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                            <div className="leading-tight">
                              <strong>Reference Mismatch:</strong>{' '}
                              {team.detected_reference_mismatch || team.validation_errors[0]}
                            </div>
                          </div>
                        )}

                        {isRevoked && (
                          <div className="mt-1.5 text-[11px] text-amber-900 bg-amber-50 border border-amber-300 rounded-lg px-2.5 py-1 flex items-start gap-1.5">
                            <RotateCcw className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                            <div className="leading-tight font-semibold">
                              Override Revoked: Underlying certificate mapping was altered. Re-review required.
                            </div>
                          </div>
                        )}

                        {!isApprovedOverride && !isRefMismatch && !isRevoked && team.validation_errors.length > 0 && (
                          <div className="text-[11px] text-rose-600 mt-1 font-sans">
                            {team.validation_errors[0]}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {getStatusBadge(team.validation_status, team.manual_override)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setSelectedTeamForOverride(team)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded-lg transition-colors border border-transparent hover:border-indigo-100"
                        >
                          <Edit className="w-3.5 h-3.5" />
                          Review / Edit
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      <ImageLightboxModal
        cert={selectedCertForModal}
        onClose={() => setSelectedCertForModal(null)}
      />

      <ManualOverrideModal
        team={selectedTeamForOverride}
        onClose={() => setSelectedTeamForOverride(null)}
        onSuccess={(updatedReport: any) => {
          if (updatedReport) {
            setValidationReport(updatedReport);
          }
        }}
      />

      <ProceedMappingModal
        isOpen={isProceedModalOpen}
        onClose={() => setIsProceedModalOpen(false)}
        summary={summary}
        mismatchedTeams={mismatchedTeams}
        sessionId={sessionId}
        onSuccess={(updatedReport) => {
          if (updatedReport) {
            setValidationReport(updatedReport);
            addToast('success', 'Option A Authorized', 'Proceeding with current mapping. Campaign creation is now unlocked.');
          }
        }}
      />
    </div>
  );
};

