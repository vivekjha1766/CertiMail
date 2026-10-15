import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  X,
  FileText,
  CheckCircle2,
  Lock,
  ArrowRight
} from 'lucide-react';
import { ValidationSummary, TeamMappingItem, apiClient, ValidationReportResponse } from '../../api/client';

interface ProceedMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (report: ValidationReportResponse) => void;
  summary: ValidationSummary;
  mismatchedTeams: TeamMappingItem[];
  sessionId: string;
}

export const ProceedMappingModal: React.FC<ProceedMappingModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  summary,
  mismatchedTeams,
  sessionId
}) => {
  const [reviewer, setReviewer] = useState('Admin Reviewer');
  const [reason, setReason] = useState('Verified certificate ordering; proceeding with existing mapper assignments');
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const hasFatalErrors = summary.has_fatal_errors || summary.missing_certificates > 0 || summary.duplicate_emails > 0;

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (hasFatalErrors) return;

    if (!reviewer.trim()) {
      setErrorMsg('Reviewer name is required.');
      return;
    }
    if (!reason.trim()) {
      setErrorMsg('An audit justification reason is required.');
      return;
    }
    if (!confirmed) {
      setErrorMsg('You must check the confirmation checkbox to authorize Option A.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const updatedReport = await apiClient.acknowledgeMismatches(
        sessionId,
        reviewer.trim(),
        reason.trim(),
        true
      );
      onSuccess(updatedReport);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to authorize current mapping.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Option A — Proceed with Current Mapping
              </h3>
              <p className="text-xs text-slate-500">
                Bulk authorization without individual team override
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleConfirm} className="flex-1 overflow-y-auto p-6 space-y-5 text-xs">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {hasFatalErrors ? (
            <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-rose-900 font-bold text-sm">
                <ShieldAlert className="w-5 h-5 text-rose-600" />
                Fatal Errors Block Option A Authorization
              </div>
              <p className="text-xs text-rose-700 leading-relaxed">
                Option A only permits waiving non-fatal <strong>reference mismatches</strong>. Your current mapping contains{' '}
                <strong>
                  {summary.missing_certificates > 0 && `${summary.missing_certificates} missing certificate file(s)`}
                  {summary.missing_certificates > 0 && summary.duplicate_emails > 0 && ' and '}
                  {summary.duplicate_emails > 0 && `${summary.duplicate_emails} duplicate email(s)`}
                </strong>
                . These fatal errors must be corrected in the uploaded files or individually overridden before dispatch.
              </p>
            </div>
          ) : (
            <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-indigo-950 font-bold text-sm">
                <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                Certificate Assignment Integrity Preserved
              </div>
              <p className="text-xs text-indigo-900 leading-relaxed">
                By choosing Option A, all certificate assignments produced by the automated mapper will be used exactly as-is.
                You are <strong>not required</strong> to inspect, approve, or override each of the {mismatchedTeams.length} affected
                teams individually. The audit log will record this explicit authorization.
              </p>
            </div>
          )}

          {/* Outstanding Issues Summary */}
          <div className="space-y-2">
            <label className="font-bold text-slate-700 uppercase tracking-wider text-[11px] flex items-center justify-between">
              <span>Unresolved Reference Mismatches Summary ({mismatchedTeams.length} Teams)</span>
              <span className="text-[10px] text-slate-400 font-normal">Preserved in validation log</span>
            </label>
            <div className="border border-slate-200 rounded-xl overflow-hidden max-h-48 overflow-y-auto divide-y divide-slate-100 bg-slate-50">
              {mismatchedTeams.length === 0 ? (
                <div className="p-4 text-center text-slate-400">No reference mismatches detected.</div>
              ) : (
                mismatchedTeams.map((t) => (
                  <div key={t.team_id} className="p-2.5 flex items-start justify-between gap-3 bg-white hover:bg-slate-50/60">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                        <span>Row {t.row_index}: {t.team_name}</span>
                        {t.team_identifier && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded font-mono bg-slate-100 text-slate-600">
                            {t.team_identifier}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        Lead: {t.leader_name} &lt;{t.leader_email}&gt;
                      </div>
                    </div>
                    <div className="text-right text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-lg max-w-[260px] truncate" title={t.detected_reference_mismatch || t.validation_errors[0]}>
                      {t.detected_reference_mismatch || t.validation_errors[0]}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Audit Inputs */}
          {!hasFatalErrors && (
            <div className="space-y-4 pt-2 border-t border-slate-200">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Reviewer Identity / Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={reviewer}
                    onChange={(e) => setReviewer(e.target.value)}
                    placeholder="e.g. Lead Organizer / Alex Chen"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-hidden text-xs"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Audit Justification / Reason <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g. Sequence offset verified against master list"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-hidden text-xs"
                  />
                </div>
              </div>

              {/* Confirmation Checkbox */}
              <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                    className="w-4 h-4 mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div className="text-xs text-amber-950 leading-relaxed font-medium">
                    I acknowledge that <strong>{mismatchedTeams.length} team(s)</strong> have reference sequence mismatches, and I explicitly confirm that the campaign will use the existing mapper certificate assignments without individual team approval overrides.
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-xl text-slate-700 hover:bg-slate-50 font-semibold text-xs transition-colors"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={loading || hasFatalErrors || !confirmed || !reviewer.trim() || !reason.trim()}
              className={`inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold text-white shadow-xs transition-all ${
                loading || hasFatalErrors || !confirmed || !reviewer.trim() || !reason.trim()
                  ? 'bg-slate-300 cursor-not-allowed text-slate-500'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {loading ? 'Authorizing...' : 'Authorize & Proceed with Current Mapping'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
