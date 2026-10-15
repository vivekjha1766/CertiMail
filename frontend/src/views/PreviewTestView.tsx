import React, { useState } from 'react';
import {
  Eye,
  Send,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Mail,
  FileCheck2,
  ArrowRight,
  ExternalLink
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient, CertificateFileInfo, TestSendResponse } from '../api/client';
import { ImageLightboxModal } from '../components/modals/ImageLightboxModal';

export const PreviewTestView: React.FC = () => {
  const {
    validationReport,
    sessionId,
    setActiveView,
    addToast,
    composedSubject,
    composedBody
  } = useApp();

  const teams = validationReport?.teams || [];
  const [selectedTeamIndex, setSelectedTeamIndex] = useState(0);
  const currentTeam = teams[selectedTeamIndex] || null;

  // Test form state
  const [testEmail, setTestEmail] = useState('');
  const [testCc, setTestCc] = useState('');
  const [testBcc, setTestBcc] = useState('');
  const [sendingTest, setSendingTest] = useState(false);
  const [testResult, setTestResult] = useState<TestSendResponse | null>(null);

  // Modal preview
  const [selectedCertForModal, setSelectedCertForModal] = useState<CertificateFileInfo | null>(null);
  const [showRecipientConfirmModal, setShowRecipientConfirmModal] = useState(false);

  const handleTriggerTestSend = () => {
    if (!testEmail || !testEmail.includes('@')) {
      addToast('warning', 'Valid Email Required', 'Please enter your test email address.');
      return;
    }
    // If CC or BCC added, require confirmation
    if (testCc || testBcc) {
      setShowRecipientConfirmModal(true);
    } else {
      executeTestSend();
    }
  };

  const executeTestSend = async () => {
    if (!currentTeam) return;
    setSendingTest(true);
    setTestResult(null);

    try {
      const res = await apiClient.sendTestEmail({
        session_id: sessionId,
        team_id: currentTeam.team_id,
        test_recipient_email: testEmail.trim(),
        subject: currentTeam.custom_subject || composedSubject,
        body: currentTeam.custom_body || composedBody,
        test_cc: testCc.trim(),
        test_bcc: testBcc.trim(),
        include_attachments: true
      });

      setTestResult(res);
      addToast('success', 'Test Email Sent!', `Delivered safely to ${testEmail}`);
      setShowRecipientConfirmModal(false);
    } catch (err: any) {
      addToast('error', 'Test Send Failed', err.response?.data?.detail || err.message);
    } finally {
      setSendingTest(false);
    }
  };

  if (teams.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <h3 className="text-lg font-bold text-slate-800">No Valid Teams Loaded</h3>
        <p className="text-sm text-slate-500">
          Upload your files in Step 2 and validate them in Step 3 before testing.
        </p>
        <button
          onClick={() => setActiveView('upload')}
          className="px-4 py-2 bg-indigo-600 text-white font-semibold text-xs rounded-xl shadow-xs"
        >
          Go to Upload Files
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Step 5: Certificate Preview & Test Mode</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Inspect real PNG certificate images for each member and safely dispatch a test email to your own address.
          </p>
        </div>

        <button
          onClick={() => setActiveView('send')}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors self-start sm:self-auto"
        >
          Proceed to Campaign Review
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Safety Notice Banner */}
      <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start gap-3.5">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        <div className="text-xs text-emerald-900 leading-relaxed">
          <strong className="font-semibold block mb-0.5">Leader Protection Active in Test Mode</strong>
          In Test Mode, the actual team leader (<code>{currentTeam?.leader_email}</code>) will <strong>never</strong> be contacted. The email and all 6 certificates are routed strictly and exclusively to the test address you specify below.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Team Selector & Certificate Thumbnails (2 cols wide on desktop) */}
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Select Team to Inspect:
                </label>
                <select
                  value={selectedTeamIndex}
                  onChange={(e) => setSelectedTeamIndex(parseInt(e.target.value))}
                  className="text-sm font-semibold px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500"
                >
                  {teams.map((t, idx) => (
                    <option key={t.team_id} value={idx}>
                      #{t.row_index}: {t.team_name} — {t.leader_name} ({t.leader_email})
                    </option>
                  ))}
                </select>
              </div>

              {currentTeam && (
                <div className="text-right">
                  <span className="text-xs font-mono text-slate-500">ID: {currentTeam.team_identifier || currentTeam.team_id}</span>
                  <div className="text-xs font-semibold text-slate-700">Leader: {currentTeam.leader_name}</div>
                </div>
              )}
            </div>

            {/* Six Certificate Thumbnails Gallery */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Six Assigned Certificates (Click any image to enlarge):
                </span>
                <span className="text-xs text-indigo-600 font-semibold">Original PNG Bytes Preserved</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5">
                {currentTeam?.certificate_files.map((cert) => (
                  <div
                    key={cert.position}
                    onClick={() => setSelectedCertForModal(cert)}
                    className="p-3 bg-slate-50 hover:bg-indigo-50/40 border border-slate-200 hover:border-indigo-300 rounded-xl cursor-pointer transition-all group flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between text-[11px] mb-1.5">
                        <span className="font-bold text-slate-700">
                          Pos #{cert.position} {cert.position === 1 ? '(Leader)' : ''}
                        </span>
                        <span className="text-slate-400 font-mono text-[10px]">{cert.filename}</span>
                      </div>

                      {/* Thumbnail Container */}
                      <div className="relative aspect-4/3 bg-slate-200 rounded-lg overflow-hidden border border-slate-300 flex items-center justify-center">
                        <img
                          src={`/api/certificates/thumbnail/${cert.batch_name.replace(' ', '_')}/${cert.filename}`}
                          alt={cert.filename}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src =
                              'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="75" viewBox="0 0 100 75"><rect fill="%23e2e8f0" width="100" height="75"/><text fill="%2394a3b8" font-family="sans-serif" font-size="9" x="50%" y="50%" dominant-baseline="middle" text-anchor="middle">Thumbnail</text></svg>';
                          }}
                        />
                        <div className="absolute inset-0 bg-indigo-950/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white">
                          <Eye className="w-5 h-5 drop-shadow-md" />
                        </div>
                      </div>
                    </div>

                    <div className="mt-2 text-center">
                      <div className="text-xs font-semibold text-slate-800 truncate" title={cert.participant_name}>
                        {cert.participant_name || `Member ${cert.position}`}
                      </div>
                      {cert.ref_number && (
                        <div className="text-[10px] text-slate-400 font-mono truncate">{cert.ref_number}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dedicated Test Send Form */}
        <div className="space-y-5">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <Mail className="w-5 h-5 text-indigo-600" />
              <h3 className="text-sm font-bold text-slate-900">Send Test Email</h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Recipient Test Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  placeholder="your-email@example.com"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
                  required
                />
                <span className="text-[11px] text-slate-400 mt-0.5 block">
                  You will receive all 6 certificates for {currentTeam?.team_name}.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Test CC (Optional, comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="co-organizer@example.com"
                  value={testCc}
                  onChange={(e) => setTestCc(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Test BCC (Optional, comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="test-archive@example.com"
                  value={testBcc}
                  onChange={(e) => setTestBcc(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={handleTriggerTestSend}
                disabled={sendingTest || !testEmail}
                className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center gap-2"
              >
                <Send className="w-4 h-4" />
                {sendingTest ? 'Sending Test Message via SMTP...' : 'Dispatch Test Email to Myself'}
              </button>
            </div>

            {/* Test Send Feedback */}
            {testResult && (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2 text-xs">
                <div className="flex items-center gap-2 text-emerald-800 font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  {testResult.message}
                </div>
                <div className="text-emerald-700 space-y-1">
                  <div>
                    Target Recipient: <span className="font-mono font-semibold">{testResult.actual_recipient}</span>
                  </div>
                  <div>
                    Team Leader Protected: <span className="font-mono">{testResult.real_leader_email_protected} (Untouched)</span>
                  </div>
                  <div>
                    Attachments Sent: <span className="font-semibold">{testResult.attachment_count} files</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modal when CC/BCC specified in test mode */}
      {showRecipientConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Confirm Test Email Recipients</h3>
            <p className="text-xs text-slate-500">
              Please review all recipients before sending the test message:
            </p>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 text-xs">
              <div>
                <span className="font-semibold text-slate-600">To:</span> <span className="font-mono text-slate-900">{testEmail}</span>
              </div>
              {testCc && (
                <div>
                  <span className="font-semibold text-slate-600">CC:</span> <span className="font-mono text-slate-900">{testCc}</span>
                </div>
              )}
              {testBcc && (
                <div>
                  <span className="font-semibold text-slate-600">BCC:</span> <span className="font-mono text-slate-900">{testBcc}</span>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowRecipientConfirmModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={executeTestSend}
                disabled={sendingTest}
                className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs"
              >
                {sendingTest ? 'Sending...' : 'Confirm & Send'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lightbox Modal */}
      <ImageLightboxModal
        cert={selectedCertForModal}
        onClose={() => setSelectedCertForModal(null)}
      />
    </div>
  );
};
