import React, { useState, useEffect } from 'react';
import {
  Send,
  Pause,
  Play,
  XOctagon,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  FileCheck,
  ShieldCheck,
  RefreshCw,
  HardDrive,
  Users,
  Edit3,
  HelpCircle,
  XCircle,
  RotateCcw,
  History,
  FileText,
  AlertCircle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import {
  apiClient,
  CampaignStatus,
  CampaignDetailResponse,
  CampaignRecipientItem,
  TemplateRevision
} from '../api/client';

export const SendCampaignView: React.FC = () => {
  const {
    validationReport,
    sessionId,
    activeCampaignId,
    setActiveCampaignId,
    setActiveView,
    addToast,
    composedSubject,
    composedBody,
    globalCc,
    globalBcc
  } = useApp();

  const [campaignName, setCampaignName] = useState(
    'Hack-O-Sprint 4.0 Certificate Distribution'
  );
  const [delaySeconds, setDelaySeconds] = useState<number>(2.0);
  const [confirmedSafe, setConfirmedSafe] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [startingSend, setStartingSend] = useState(false);

  // Live Campaign Progress & Detail State
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus | null>(null);
  const [campaignDetail, setCampaignDetail] = useState<CampaignDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Modals
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [revisionChoice, setRevisionChoice] = useState<'OPTION_B_APPLY_TO_REMAINING' | 'OPTION_A_KEEP_ORIGINAL'>('OPTION_B_APPLY_TO_REMAINING');
  const [revSubject, setRevSubject] = useState('');
  const [revBody, setRevBody] = useState('');
  const [revCc, setRevCc] = useState('');
  const [revBcc, setRevBcc] = useState('');
  const [revReviewer, setRevReviewer] = useState('Admin');
  const [revReason, setRevReason] = useState('Template updated for remaining recipients');
  const [savingRevision, setSavingRevision] = useState(false);

  const [resolvingRecipient, setResolvingRecipient] = useState<CampaignRecipientItem | null>(null);
  const [uncertainAction, setUncertainAction] = useState<'authorize_retry' | 'mark_accepted' | 'mark_skipped'>('authorize_retry');
  const [uncertainReason, setUncertainReason] = useState('Reviewed transmission logs; confirmed safe to retry.');
  const [savingResolution, setSavingResolution] = useState(false);

  const [retryingFailed, setRetryingFailed] = useState(false);

  const report = validationReport;
  const teams = report?.teams || [];
  const totalTeams = teams.length;
  const totalCerts = totalTeams * 6;
  const uniqueEmails = new Set(teams.map((t) => t.leader_email.toLowerCase())).size;
  const overrideCount = teams.filter((t) => t.manual_override).length;

  // Poll status & fetch detail
  useEffect(() => {
    let interval: any = null;
    if (activeCampaignId) {
      loadCampaignDetail(activeCampaignId);
      const poll = async () => {
        try {
          const st = await apiClient.getCampaignStatus(activeCampaignId);
          setCampaignStatus(st);
          if (st.status === 'sending') {
            loadCampaignDetail(activeCampaignId);
          }
          if (st.is_completed) {
            clearInterval(interval);
            loadCampaignDetail(activeCampaignId);
          }
        } catch (e) {
          // ignore
        }
      };
      poll();
      interval = setInterval(poll, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeCampaignId]);

  const loadCampaignDetail = async (cId: string) => {
    try {
      const detail = await apiClient.getCampaignDetail(cId);
      setCampaignDetail(detail);
    } catch (e) {
      // ignore
    }
  };

  const handlePrepareCampaign = async () => {
    if (!report?.summary.can_send) {
      addToast('error', 'Cannot Prepare', 'Unresolved validation errors exist. Please resolve them first.');
      return;
    }

    setPreparing(true);
    try {
      const ack = report.summary.mismatch_acknowledgement;
      const res = await apiClient.createCampaign({
        name: campaignName,
        session_id: sessionId,
        subject: composedSubject,
        body: composedBody,
        global_cc: globalCc,
        global_bcc: globalBcc,
        delay_seconds: delaySeconds,
        proceed_with_current_mapping: Boolean(ack),
        mismatch_ack_reviewer: ack?.reviewer,
        mismatch_ack_reason: ack?.reason,
        mismatch_ack_confirmed: Boolean(ack)
      });

      setActiveCampaignId(res.id);
      addToast('success', 'Campaign Prepared (Mode A)', `Prepared ${res.total_teams} messages with Revision 1. Ready for sequential dispatch.`);
      loadCampaignDetail(res.id);
    } catch (err: any) {
      addToast('error', 'Preparation Failed', err.response?.data?.detail || err.message);
    } finally {
      setPreparing(false);
    }
  };

  const handleStartSending = async () => {
    if (!confirmedSafe) {
      addToast('warning', 'Confirmation Required', 'Please check the final authorization confirmation box.');
      return;
    }

    setStartingSend(true);
    try {
      let targetCampId = activeCampaignId;
      if (!targetCampId) {
        // Create campaign first using active composed subject and body
        const ack = report?.summary.mismatch_acknowledgement;
        const campRes = await apiClient.createCampaign({
          name: campaignName,
          session_id: sessionId,
          subject: composedSubject,
          body: composedBody,
          global_cc: globalCc,
          global_bcc: globalBcc,
          delay_seconds: delaySeconds,
          proceed_with_current_mapping: Boolean(ack),
          mismatch_ack_reviewer: ack?.reviewer,
          mismatch_ack_reason: ack?.reason,
          mismatch_ack_confirmed: Boolean(ack)
        });
        targetCampId = campRes.id;
        setActiveCampaignId(campRes.id);
      }
      if (!targetCampId) return;

      await apiClient.startCampaign(targetCampId, {
        delay_seconds: delaySeconds,
        max_retries: 2
      });

      addToast('info', 'Bulk Delivery Started (Mode B)', 'Emails are now being sequentially delivered via SMTP.');
      loadCampaignDetail(targetCampId);
    } catch (err: any) {
      addToast('error', 'Start Failed', err.response?.data?.detail || err.message);
    } finally {
      setStartingSend(false);
    }
  };

  const handlePause = async () => {
    if (!activeCampaignId) return;
    try {
      await apiClient.pauseCampaign(activeCampaignId);
      addToast('info', 'Pause Requested', 'Dispatcher will stop after current message reaches a safe checkpoint.');
      if (activeCampaignId) loadCampaignDetail(activeCampaignId);
    } catch (e: any) {
      addToast('error', 'Pause Failed', e.message);
    }
  };

  const handleResume = async () => {
    if (!activeCampaignId) return;
    try {
      await apiClient.resumeCampaign(activeCampaignId, {
        delay_seconds: delaySeconds,
        max_retries: 2
      });
      addToast('success', 'Campaign Resumed', 'Safe continuation active. Already accepted recipients will not be resent.');
      if (activeCampaignId) loadCampaignDetail(activeCampaignId);
    } catch (e: any) {
      addToast('error', 'Resume Failed', e.message);
    }
  };

  const handleCancel = async () => {
    if (!activeCampaignId) return;
    if (confirm('Are you sure you want to cancel remaining unsent emails in this campaign? Existing delivery records will be preserved.')) {
      try {
        await apiClient.cancelCampaign(activeCampaignId);
        addToast('warning', 'Campaign Cancelled', 'Remaining unsent emails stopped.');
        if (activeCampaignId) loadCampaignDetail(activeCampaignId);
      } catch (e: any) {
        addToast('error', 'Cancel Failed', e.message);
      }
    }
  };

  const handleOpenRevisionModal = () => {
    const activeRev = campaignDetail?.revisions.find((r) => r.is_active) || campaignDetail?.revisions[campaignDetail.revisions.length - 1];
    setRevSubject(activeRev ? activeRev.subject : composedSubject);
    setRevBody(activeRev ? activeRev.body : composedBody);
    setRevCc(activeRev ? activeRev.global_cc : globalCc);
    setRevBcc(activeRev ? activeRev.global_bcc : globalBcc);
    setShowRevisionModal(true);
  };

  const handleSaveRevision = async () => {
    if (!activeCampaignId) return;
    setSavingRevision(true);
    try {
      const res = await apiClient.updateCampaignTemplate(activeCampaignId, {
        choice: revisionChoice,
        subject: revSubject,
        body: revBody,
        global_cc: revCc,
        global_bcc: revBcc,
        reviewer: revReviewer,
        reason: revReason
      });

      addToast('success', 'Template Revision Updated', res.message);
      setShowRevisionModal(false);
      loadCampaignDetail(activeCampaignId);
    } catch (err: any) {
      addToast('error', 'Revision Failed', err.response?.data?.detail || err.message);
    } finally {
      setSavingRevision(false);
    }
  };

  const handleResolveUncertain = async () => {
    if (!activeCampaignId || !resolvingRecipient) return;
    setSavingResolution(true);
    try {
      const res = await apiClient.resolveUncertainDelivery(activeCampaignId, {
        recipient_id: resolvingRecipient.recipient_id || resolvingRecipient.id,
        action: uncertainAction,
        reviewer: 'Admin',
        reason: uncertainReason
      });
      addToast('success', 'Uncertain Delivery Resolved', res.message);
      setResolvingRecipient(null);
      loadCampaignDetail(activeCampaignId);
    } catch (err: any) {
      addToast('error', 'Resolution Failed', err.response?.data?.detail || err.message);
    } finally {
      setSavingResolution(false);
    }
  };

  const handleRetryFailedBatch = async () => {
    if (!activeCampaignId) return;
    setRetryingFailed(true);
    try {
      const res = await apiClient.retryFailedRecipients(activeCampaignId, {
        reviewer: 'Admin',
        reason: 'Authorized batch retry for all failed recipients.'
      });
      addToast('success', 'Failed Recipients Authorized', res.message);
      loadCampaignDetail(activeCampaignId);
    } catch (err: any) {
      addToast('error', 'Retry Authorization Failed', err.response?.data?.detail || err.message);
    } finally {
      setRetryingFailed(false);
    }
  };

  if (!report && !campaignDetail) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <h3 className="text-lg font-bold text-slate-800">No Campaign Selected</h3>
        <p className="text-sm text-slate-500">
          Upload and validate files first, or select an existing campaign from the Recovery Console.
        </p>
        <div className="flex justify-center gap-3">
          <button
            onClick={() => setActiveView('upload')}
            className="px-4 py-2 bg-indigo-600 text-white font-semibold text-xs rounded-xl shadow-xs"
          >
            Go to Upload Files
          </button>
          <button
            onClick={() => setActiveView('recovery')}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl shadow-xs"
          >
            Open Recovery Console
          </button>
        </div>
      </div>
    );
  }

  const isSending = campaignStatus?.status === 'sending';
  const isPaused = campaignStatus?.is_paused;
  const counts = campaignDetail?.summary_counts || {
    total: totalTeams,
    accepted: 0,
    pending: totalTeams,
    failed: 0,
    uncertain: 0,
    skipped: 0
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Step 6: Campaign Dispatch, Checkpoints & Resumption
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Sequential bulk delivery with checkpointed pause/resume, immutable template revisions, and recipient-level delivery ledger.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveView('recovery')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-colors shadow-2xs"
          >
            <RotateCcw className="w-3.5 h-3.5 text-indigo-600" />
            Recovery Console
          </button>
        </div>
      </div>

      {/* Review Metrics Summary Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs text-slate-500 font-medium">Total Recipients</span>
          <div className="text-xl font-bold text-slate-900 mt-1">{counts.total}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs text-slate-500 font-medium">SMTP Accepted</span>
          <div className="text-xl font-bold text-emerald-600 mt-1">{counts.accepted}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs text-slate-500 font-medium">Pending Delivery</span>
          <div className="text-xl font-bold text-indigo-600 mt-1">{counts.pending}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs text-slate-500 font-medium">Failed</span>
          <div className="text-xl font-bold text-rose-600 mt-1">{counts.failed}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs text-slate-500 font-medium">Delivery Uncertain</span>
          <div className="text-xl font-bold text-amber-600 mt-1">{counts.uncertain}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-xs text-slate-500 font-medium">Active Template Rev</span>
          <div className="text-xl font-bold text-purple-600 mt-1">
            Rev {campaignDetail?.campaign.current_template_revision || 1}
          </div>
        </div>
      </div>

      {/* Live Sending & Control Monitor */}
      {activeCampaignId && (
        <div className="bg-white rounded-2xl border border-indigo-200 p-6 shadow-md space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  isSending
                    ? 'bg-indigo-600 text-white animate-pulse'
                    : isPaused
                    ? 'bg-amber-100 text-amber-700'
                    : campaignStatus?.status === 'completed'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-rose-600 text-white'
                }`}
              >
                {isSending ? <Send className="w-5 h-5" /> : isPaused ? <Pause className="w-5 h-5" /> : <CheckCircle2 className="w-5 h-5" />}
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  Campaign Status:{' '}
                  <span className="uppercase text-indigo-700">{campaignStatus?.status || campaignDetail?.campaign.status || 'prepared'}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-semibold border border-purple-200">
                    Template Rev {campaignDetail?.campaign.current_template_revision || 1}
                  </span>
                </h3>
                {campaignStatus?.current_team && (
                  <p className="text-xs text-slate-500 mt-0.5">
                    Currently delivering: <strong className="text-slate-800">{campaignStatus.current_team}</strong>
                  </p>
                )}
              </div>
            </div>

            {/* Checkpoint Controls */}
            <div className="flex flex-wrap items-center gap-2">
              {isSending && (
                <button
                  onClick={handlePause}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold rounded-xl border border-amber-200 transition-colors"
                >
                  <Pause className="w-3.5 h-3.5" />
                  Pause at Next Checkpoint
                </button>
              )}

              {(isPaused || campaignStatus?.status === 'interrupted' || campaignStatus?.status === 'prepared' || campaignStatus?.status === 'failed') && (
                <button
                  onClick={handleResume}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
                >
                  <Play className="w-3.5 h-3.5" />
                  Resume Safe Sending
                </button>
              )}

              {/* Edit Template during Pause */}
              {isPaused && (
                <button
                  onClick={handleOpenRevisionModal}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold rounded-xl border border-purple-200 transition-colors"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Edit Template Revision
                </button>
              )}

              {counts.failed > 0 && !isSending && (
                <button
                  onClick={handleRetryFailedBatch}
                  disabled={retryingFailed}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold rounded-xl border border-rose-200 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Retry Failed ({counts.failed})
                </button>
              )}

              {(isSending || isPaused) && (
                <button
                  onClick={handleCancel}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold rounded-xl border border-rose-200 transition-colors"
                >
                  <XOctagon className="w-3.5 h-3.5" />
                  Cancel Remaining
                </button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div>
            <div className="flex justify-between text-xs font-bold text-slate-600 mb-1.5">
              <span>Overall Completed Deliveries ({Math.round(((counts.accepted + counts.failed) / (counts.total || 1)) * 100)}%)</span>
              <span>
                {counts.accepted + counts.failed} / {counts.total} Handled
              </span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-300"
                style={{ width: `${Math.min(100, ((counts.accepted + counts.failed) / (counts.total || 1)) * 100)}%` }}
              />
            </div>
          </div>

          {campaignStatus?.error_message && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800">
              {campaignStatus.error_message}
            </div>
          )}
        </div>
      )}

      {/* Recipient-Level Delivery Ledger Table */}
      {campaignDetail && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden space-y-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-600" />
                Authoritative Recipient Delivery Ledger
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every recipient is tracked independently. Reordering rows will never cause duplicate deliveries or wrong certificate mappings.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">
                {campaignDetail.recipients.length} records registered
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Recipient Identifier / Team</th>
                  <th className="py-2.5 px-3">Normalized Leader Email</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                  <th className="py-2.5 px-3 text-center">Attempts</th>
                  <th className="py-2.5 px-3 text-center">Template Rev</th>
                  <th className="py-2.5 px-3">Timestamp / Outcome</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {campaignDetail.recipients.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-2.5 px-3 font-medium">
                      <div className="font-semibold text-slate-900">{rec.team_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{rec.team_identifier || rec.recipient_id}</div>
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {rec.normalized_email}
                      <div className="text-[11px] text-slate-400">{rec.leader_name}</div>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {rec.delivery_status === 'SMTP_ACCEPTED' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="w-3 h-3" /> Accepted
                        </span>
                      )}
                      {rec.delivery_status === 'IN_PROGRESS' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-100 text-indigo-700 animate-pulse">
                          <RefreshCw className="w-3 h-3 animate-spin" /> In Progress
                        </span>
                      )}
                      {rec.delivery_status === 'PENDING' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600">
                          Pending
                        </span>
                      )}
                      {rec.delivery_status === 'FAILED' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-100 text-rose-800">
                          <XCircle className="w-3 h-3" /> Failed
                        </span>
                      )}
                      {rec.delivery_status === 'DELIVERY_UNKNOWN' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">
                          <HelpCircle className="w-3 h-3" /> Uncertain
                        </span>
                      )}
                      {rec.delivery_status === 'SKIPPED' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-200 text-slate-700">
                          Skipped
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center font-semibold">{rec.delivery_attempts}</td>
                    <td className="py-2.5 px-3 text-center font-bold text-purple-700">Rev {rec.template_revision_used}</td>
                    <td className="py-2.5 px-3 text-[11px]">
                      {rec.delivery_timestamp && (
                        <div className="text-slate-500">{new Date(rec.delivery_timestamp).toLocaleTimeString()}</div>
                      )}
                      {rec.last_error && (
                        <div className="text-rose-600 truncate max-w-[200px]" title={rec.last_error}>
                          {rec.last_error}
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {rec.delivery_status === 'DELIVERY_UNKNOWN' && (
                        <button
                          onClick={() => {
                            setResolvingRecipient(rec);
                            setUncertainAction('authorize_retry');
                          }}
                          className="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold text-[11px] rounded-lg border border-amber-200 transition-colors"
                        >
                          Resolve Uncertain
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Campaign Settings & Launch Card (When preparing or re-dispatching) */}
      {!activeCampaignId && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900">Campaign Dispatch Parameters</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Configure delays to respect your SMTP provider's rate limits (recommended: 1.5 - 3.0 seconds per email).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Campaign Title</label>
              <input
                type="text"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Inter-Message Delay (Seconds)
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="10.0"
                value={delaySeconds}
                onChange={(e) => setDelaySeconds(parseFloat(e.target.value) || 2.0)}
                className="w-full px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Explicit Confirmation Checkbox */}
          <div className="p-4 bg-indigo-50/60 border border-indigo-200 rounded-xl flex items-start gap-3">
            <input
              type="checkbox"
              id="campaign-confirm"
              checked={confirmedSafe}
              onChange={(e) => setConfirmedSafe(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="campaign-confirm" className="text-xs text-slate-700 leading-relaxed cursor-pointer">
              <strong className="text-indigo-950 block mb-0.5">Explicit Authorization for Bulk Sending</strong>
              I verify that I have previewed the message template, inspected certificate thumbnails, and tested email delivery with my personal address. I authorize sequential SMTP delivery of <strong>{totalTeams} emails</strong> (each with 6 certificate attachments).
            </label>
          </div>

          {/* Action Buttons: Mode A vs Mode B */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-100">
            <div>
              <span className="text-[11px] text-slate-400 block">
                Notice: SMTP acceptance confirms handoff to mail server; recipient inbox delivery depends on destination server.
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handlePrepareCampaign}
                disabled={preparing || isSending}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-colors shadow-2xs"
              >
                {preparing ? 'Preparing...' : 'Mode A: Prepare Manifest Only'}
              </button>

              <button
                onClick={handleStartSending}
                disabled={startingSend || isSending || !confirmedSafe}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-bold text-xs rounded-xl shadow-md transition-colors"
              >
                <Send className="w-4 h-4" />
                {startingSend ? 'Starting...' : 'Mode B: Start Bulk Campaign'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Template Revision Modal (Option A vs Option B) */}
      {showRevisionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Edit Campaign Template Revision</h3>
              </div>
              <button
                onClick={() => setShowRevisionModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xs font-semibold"
              >
                Cancel
              </button>
            </div>

            {/* Confirmation Summary Table */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
              <div className="font-bold text-slate-700">Campaign Continuation Summary:</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">Already Accepted</span>
                  <strong className="text-emerald-700 font-bold">{counts.accepted}</strong>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">Pending Remaining</span>
                  <strong className="text-indigo-700 font-bold">{counts.pending}</strong>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">Failed</span>
                  <strong className="text-rose-700 font-bold">{counts.failed}</strong>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">Delivery Uncertain</span>
                  <strong className="text-amber-700 font-bold">{counts.uncertain}</strong>
                </div>
              </div>
            </div>

            {/* Revision Option Selection */}
            <div className="space-y-3">
              <label className="block text-xs font-bold text-slate-700">Choose Revision Application Policy:</label>
              
              <div
                onClick={() => setRevisionChoice('OPTION_B_APPLY_TO_REMAINING')}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  revisionChoice === 'OPTION_B_APPLY_TO_REMAINING'
                    ? 'bg-indigo-50/70 border-indigo-400 ring-2 ring-indigo-500/20'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <input
                    type="radio"
                    name="revChoice"
                    checked={revisionChoice === 'OPTION_B_APPLY_TO_REMAINING'}
                    onChange={() => setRevisionChoice('OPTION_B_APPLY_TO_REMAINING')}
                    className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <strong className="text-xs text-slate-900 block font-bold">
                      Option B — Apply updated template to remaining recipients (Recommended)
                    </strong>
                    <span className="text-[11px] text-slate-500 leading-relaxed block mt-0.5">
                      Creates an immutable new template revision (Revision {(campaignDetail?.campaign.current_template_revision || 1) + 1}) used strictly for recipients who have not yet had their emails accepted by SMTP. Already accepted deliveries remain immutable in history.
                    </span>
                  </div>
                </div>
              </div>

              <div
                onClick={() => setRevisionChoice('OPTION_A_KEEP_ORIGINAL')}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  revisionChoice === 'OPTION_A_KEEP_ORIGINAL'
                    ? 'bg-indigo-50/70 border-indigo-400 ring-2 ring-indigo-500/20'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <input
                    type="radio"
                    name="revChoice"
                    checked={revisionChoice === 'OPTION_A_KEEP_ORIGINAL'}
                    onChange={() => setRevisionChoice('OPTION_A_KEEP_ORIGINAL')}
                    className="mt-0.5 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <strong className="text-xs text-slate-900 block font-bold">
                      Option A — Continue with the original template
                    </strong>
                    <span className="text-[11px] text-slate-500 leading-relaxed block mt-0.5">
                      Keep the original campaign template revision (Revision {campaignDetail?.campaign.current_template_revision || 1}) for all remaining recipients.
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Subject & Body Editor */}
            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Subject</label>
                <input
                  type="text"
                  value={revSubject}
                  onChange={(e) => setRevSubject(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Body Text</label>
                <textarea
                  rows={8}
                  value={revBody}
                  onChange={(e) => setRevBody(e.target.value)}
                  className="w-full p-3 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500 font-sans"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Reviewer Name</label>
                  <input
                    type="text"
                    value={revReviewer}
                    onChange={(e) => setRevReviewer(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Change Reason</label>
                  <input
                    type="text"
                    value={revReason}
                    onChange={(e) => setRevReason(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                onClick={() => setShowRevisionModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRevision}
                disabled={savingRevision}
                className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs"
              >
                {savingRevision ? 'Saving...' : 'Apply Revision & Continue'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Uncertain Delivery Resolution Modal */}
      {resolvingRecipient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center gap-2 text-amber-700">
              <HelpCircle className="w-5 h-5 text-amber-600" />
              <h3 className="text-base font-bold text-slate-900">Resolve Uncertain Delivery Outcome</h3>
            </div>

            <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 leading-relaxed space-y-2">
              <strong className="block font-semibold">Important Delivery Warning:</strong>
              CertiMail's connection dropped mid-transmission while sending to <strong className="font-mono">{resolvingRecipient.normalized_email}</strong>. The remote SMTP mail server may or may not have received and queued this message.
              <p className="text-[11px] text-amber-800">
                Resending an email that was accepted may cause a duplicate delivery to the team leader.
              </p>
            </div>

            <div className="space-y-2.5">
              <label className="block text-xs font-bold text-slate-700">Resolution Action:</label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="radio"
                  name="uncertainAct"
                  checked={uncertainAction === 'authorize_retry'}
                  onChange={() => setUncertainAction('authorize_retry')}
                  className="mt-0.5 text-indigo-600"
                />
                <div className="text-xs">
                  <strong className="block text-slate-900">Authorize Retry</strong>
                  <span className="text-slate-500 text-[11px]">Allow CertiMail to dispatch this message again when sending resumes.</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="radio"
                  name="uncertainAct"
                  checked={uncertainAction === 'mark_accepted'}
                  onChange={() => setUncertainAction('mark_accepted')}
                  className="mt-0.5 text-emerald-600"
                />
                <div className="text-xs">
                  <strong className="block text-slate-900">Mark as Accepted</strong>
                  <span className="text-slate-500 text-[11px]">Confirm receipt externally (e.g. via logs or recipient response) and record as accepted.</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-50">
                <input
                  type="radio"
                  name="uncertainAct"
                  checked={uncertainAction === 'mark_skipped'}
                  onChange={() => setUncertainAction('mark_skipped')}
                  className="mt-0.5 text-slate-600"
                />
                <div className="text-xs">
                  <strong className="block text-slate-900">Mark as Skipped</strong>
                  <span className="text-slate-500 text-[11px]">Skip this recipient and exclude them from future automatic dispatches.</span>
                </div>
              </label>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Resolution Audit Reason</label>
              <input
                type="text"
                value={uncertainReason}
                onChange={(e) => setUncertainReason(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setResolvingRecipient(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleResolveUncertain}
                disabled={savingResolution}
                className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs"
              >
                {savingResolution ? 'Saving...' : 'Confirm Resolution'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
