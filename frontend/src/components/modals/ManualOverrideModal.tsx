import React, { useState } from 'react';
import { X, CheckCircle2, AlertTriangle, ShieldCheck, ShieldAlert, FileText, UserCheck, RotateCcw } from 'lucide-react';
import { TeamMappingItem, apiClient } from '../../api/client';
import { useApp } from '../../context/AppContext';

interface ManualOverrideModalProps {
  team: TeamMappingItem | null;
  onClose: () => void;
  onSuccess: (updatedReport: any) => void;
}

export const ManualOverrideModal: React.FC<ManualOverrideModalProps> = ({ team, onClose, onSuccess }) => {
  const { sessionId, addToast } = useApp();

  if (!team) return null;

  const [leaderEmail, setLeaderEmail] = useState(team.leader_email);
  const [leaderName, setLeaderName] = useState(team.leader_name);
  const [ccRecipients, setCcRecipients] = useState(team.cc_recipients || '');
  const [bccRecipients, setBccRecipients] = useState(team.bcc_recipients || '');
  const [certFiles, setCertFiles] = useState<string[]>(
    team.certificate_files.map((c) => c.filename || `${team.row_index}.png`)
  );
  
  // Status and Audit fields
  const [overrideStatus, setOverrideStatus] = useState<string>(
    team.override_status || (team.validation_status === 'OVERRIDE_APPROVED' ? 'OVERRIDE_APPROVED' : 'OVERRIDE_APPROVED')
  );
  const [reviewer, setReviewer] = useState<string>(team.override_reviewer || 'Lead Organizer / Admin');
  const [reason, setReason] = useState<string>(team.override_reason || '');
  const [confirmedAuth, setConfirmedAuth] = useState(true);
  const [saving, setSaving] = useState(false);

  const isRefMismatch = team.validation_status === 'REFERENCE_MISMATCH' || Boolean(team.detected_reference_mismatch);

  const handleCertChange = (posIndex: number, val: string) => {
    const updated = [...certFiles];
    updated[posIndex] = val;
    setCertFiles(updated);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (overrideStatus === 'OVERRIDE_APPROVED') {
      if (!confirmedAuth) {
        addToast('warning', 'Authorization Required', 'Please confirm the explicit approval authorization checkbox before saving.');
        return;
      }
      if (!reason.trim()) {
        addToast('warning', 'Approval Reason Required', 'Please provide a justification for this override for audit tracking.');
        return;
      }
      if (!reviewer.trim()) {
        addToast('warning', 'Reviewer Required', 'Please identify the authorized reviewer.');
        return;
      }
    }

    setSaving(true);
    try {
      const updatedReport = await apiClient.submitOverride({
        session_id: sessionId,
        team_id: team.team_id,
        team_identifier: team.team_identifier,
        row_index: team.row_index,
        leader_email: leaderEmail.trim(),
        leader_name: leaderName.trim(),
        cc_recipients: ccRecipients.trim(),
        bcc_recipients: bccRecipients.trim(),
        certificate_filenames: certFiles,
        status: overrideStatus,
        reviewer: reviewer.trim(),
        reason: reason.trim() || 'Reviewed and authorized by administrator',
        approve_override: overrideStatus === 'OVERRIDE_APPROVED'
      });

      addToast(
        'success',
        'Override Persisted',
        `Override for ${team.team_name} saved as ${overrideStatus.replace('_', ' ')}.`
      );
      onSuccess(updatedReport);
      onClose();
    } catch (err: any) {
      // Preserves form input on failure
      const errorMsg = err.response?.data?.detail || err.message || 'Unknown database write error.';
      addToast('error', 'Failed to Save Override', errorMsg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto">
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full my-8 border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-slate-900">
                Manual Override & Review: {team.team_name}
              </h3>
              <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-200 text-slate-700">
                Row #{team.row_index}
              </span>
              {team.team_identifier && (
                <span className="text-xs px-2 py-0.5 rounded font-mono bg-indigo-100 text-indigo-700">
                  {team.team_identifier}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Review reference mismatches or update certificate assignments with strict audit persistence.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-5">
          {/* Reference Mismatch Special Audit Panel */}
          {isRefMismatch && (
            <div className="p-4 bg-amber-50/80 border border-amber-300 rounded-xl space-y-2 text-xs text-amber-900">
              <div className="font-bold flex items-center gap-1.5 text-amber-950">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Reference Mismatch Audit Inspection:
              </div>
              <p className="text-amber-800 leading-relaxed">
                The Excel participant reference number sequence does not align with the certificate numbering.
                You can review this discrepancy and explicitly authorize an approved override. The original detected
                reference will remain preserved for audit compliance.
              </p>
              {team.detected_reference_mismatch && (
                <div className="p-2 bg-white/80 border border-amber-200 rounded font-mono text-[11px] text-amber-900">
                  {team.detected_reference_mismatch}
                </div>
              )}
            </div>
          )}

          {/* Validation Warnings Alert if any other errors */}
          {team.validation_errors.length > 0 && !isRefMismatch && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl space-y-1 text-xs text-rose-800">
              <div className="font-semibold flex items-center gap-1.5 text-rose-900">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                Current Issues Detected:
              </div>
              <ul className="list-disc pl-5 space-y-0.5">
                {team.validation_errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Override Action Decision */}
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <label className="block text-xs font-bold text-slate-800">
              Override Decision & Action
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setOverrideStatus('OVERRIDE_APPROVED')}
                className={`flex items-center justify-center gap-1.5 p-2 rounded-lg text-xs font-semibold border transition-all ${
                  overrideStatus === 'OVERRIDE_APPROVED'
                    ? 'bg-emerald-600 text-white border-emerald-700 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                Approve Override
              </button>
              <button
                type="button"
                onClick={() => setOverrideStatus('OVERRIDE_REJECTED')}
                className={`flex items-center justify-center gap-1.5 p-2 rounded-lg text-xs font-semibold border transition-all ${
                  overrideStatus === 'OVERRIDE_REJECTED'
                    ? 'bg-rose-600 text-white border-rose-700 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                <ShieldAlert className="w-4 h-4" />
                Reject Override
              </button>
              <button
                type="button"
                onClick={() => setOverrideStatus('OVERRIDE_REVOKED')}
                className={`flex items-center justify-center gap-1.5 p-2 rounded-lg text-xs font-semibold border transition-all ${
                  overrideStatus === 'OVERRIDE_REVOKED'
                    ? 'bg-amber-600 text-white border-amber-700 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                }`}
              >
                <RotateCcw className="w-4 h-4" />
                Revoke Override
              </button>
            </div>
          </div>

          {/* Reviewer & Reason for Audit Trail */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Authorized Reviewer Name <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <UserCheck className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={reviewer}
                  onChange={(e) => setReviewer(e.target.value)}
                  placeholder="e.g. Lead Organizer / Admin"
                  className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Review Reason / Justification <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <FileText className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g. Verified offline registration sheet; authorized distribution"
                  className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white"
                  required
                />
              </div>
            </div>
          </div>

          {/* Leader Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Leader Name</label>
              <input
                type="text"
                value={leaderName}
                onChange={(e) => setLeaderName(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Leader Email (To:)</label>
              <input
                type="email"
                value={leaderEmail}
                onChange={(e) => setLeaderEmail(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white"
                required
              />
            </div>
          </div>

          {/* CC / BCC Overrides */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Per-Team CC (Visible, comma-separated)
              </label>
              <input
                type="text"
                value={ccRecipients}
                onChange={(e) => setCcRecipients(e.target.value)}
                placeholder="mentor@univ.edu, lead2@team.org"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Per-Team BCC (Hidden, comma-separated)
              </label>
              <input
                type="text"
                value={bccRecipients}
                onChange={(e) => setBccRecipients(e.target.value)}
                placeholder="archive@univ.edu"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 focus:bg-white"
              />
            </div>
          </div>

          {/* 6 Certificate File Assignments */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-slate-700">
                Assigned Certificate Filenames (Positions 1 to 6)
              </label>
              <span className="text-[10px] text-slate-500">
                Changing files automatically binds to approved mapping hash
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {[0, 1, 2, 3, 4, 5].map((idx) => {
                const pName = team.participant_names[idx] || `Member ${idx + 1}`;
                const refVal = team.ref_numbers[idx] || '';
                return (
                  <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                    <span className="text-[11px] font-medium text-slate-500 block truncate mb-0.5">
                      Pos {idx + 1}: <strong className="text-slate-700">{pName}</strong>
                    </span>
                    {refVal && (
                      <span className="text-[10px] text-indigo-600 font-mono block truncate mb-1">
                        Ref: {refVal}
                      </span>
                    )}
                    <input
                      type="text"
                      value={certFiles[idx] || ''}
                      onChange={(e) => handleCertChange(idx, e.target.value)}
                      placeholder={`${team.row_index}.png`}
                      className="w-full px-2 py-1 text-xs font-mono bg-white border border-slate-300 rounded focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Explicit Authorization Checkbox */}
          {overrideStatus === 'OVERRIDE_APPROVED' && (
            <div className="p-3.5 bg-indigo-50/70 border border-indigo-200 rounded-xl flex items-start gap-3">
              <input
                type="checkbox"
                id="approve-override"
                checked={confirmedAuth}
                onChange={(e) => setConfirmedAuth(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="approve-override" className="text-xs text-slate-700 leading-relaxed cursor-pointer">
                <strong className="text-indigo-900 block mb-0.5">Explicit Authorization & Audit Acknowledgement</strong>
                I confirm that I have reviewed this team's certificate assignment and reference numbers.
                I authorize this override and understand this approval will be logged to SQLite audit records.
              </label>
            </div>
          )}

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className={`px-5 py-2 text-xs font-semibold text-white rounded-lg transition-all shadow-xs flex items-center gap-2 ${
                overrideStatus === 'OVERRIDE_APPROVED'
                  ? 'bg-indigo-600 hover:bg-indigo-700'
                  : overrideStatus === 'OVERRIDE_REJECTED'
                  ? 'bg-rose-600 hover:bg-rose-700'
                  : 'bg-amber-600 hover:bg-amber-700'
              }`}
            >
              {saving ? 'Persisting...' : 'Save Override to Database'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
