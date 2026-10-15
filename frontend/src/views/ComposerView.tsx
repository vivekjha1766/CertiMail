import React, { useState, useEffect } from 'react';
import {
  Mail,
  Save,
  FolderOpen,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Eye,
  Copy,
  Plus
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient, TemplateItem } from '../api/client';

export const ComposerView: React.FC = () => {
  const {
    validationReport,
    setActiveView,
    addToast,
    composedSubject: subject,
    setComposedSubject: setSubject,
    composedBody: body,
    setComposedBody: setBody,
    globalCc,
    setGlobalCc,
    globalBcc,
    setGlobalBcc
  } = useApp();

  // Templates
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [newTemplateName, setNewTemplateName] = useState('');
  const [savingTemplate, setSavingTemplate] = useState(false);

  // Live Preview
  const [selectedPreviewTeamIndex, setSelectedPreviewTeamIndex] = useState(0);
  const [previewRendered, setPreviewRendered] = useState<{
    subject: string;
    body: string;
    missing: string[];
  }>({ subject: '', body: '', missing: [] });

  const teams = validationReport?.teams || [];
  const currentTeam = teams[selectedPreviewTeamIndex] || null;

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const list = await apiClient.getTemplates();
      setTemplates(list);
      if (list.length > 0 && !selectedTemplateId) {
        setSelectedTemplateId(list[0].id);
      }
    } catch (e) {
      // ignore
    }
  };

  const handleSelectTemplate = (id: string) => {
    setSelectedTemplateId(id);
    const tmpl = templates.find((t) => t.id === id);
    if (tmpl) {
      setSubject(tmpl.subject);
      setBody(tmpl.body);
      addToast('info', 'Template Loaded', `Loaded "${tmpl.name}"`);
    }
  };

  const handleSaveAsTemplate = async () => {
    if (!newTemplateName.trim()) {
      addToast('warning', 'Name Required', 'Please enter a name for the new template.');
      return;
    }
    setSavingTemplate(true);
    try {
      const created = await apiClient.createTemplate({
        name: newTemplateName.trim(),
        subject,
        body
      });
      setTemplates((prev) => [created, ...prev]);
      setSelectedTemplateId(created.id);
      setNewTemplateName('');
      addToast('success', 'Template Saved', `"${created.name}" is now available in your templates.`);
    } catch (err: any) {
      addToast('error', 'Save Failed', err.response?.data?.detail || err.message);
    } finally {
      setSavingTemplate(false);
    }
  };

  // Render preview on text or team change
  useEffect(() => {
    if (!currentTeam) {
      // Mock team data
      const mockTeam = {
        team_name: 'Quantum Coders 1',
        leader_name: 'Aarav Sharma',
        leader_email: 'aarav.sharma@example.com',
        team_id: 'HOS-2026-T001',
        event_name: 'Hack-O-Sprint 4.0 – SIH Internal Round 2026',
        member_1: 'Aarav Sharma',
        member_2: 'Diya Patel',
        member_3: 'Rohan Verma',
        member_4: 'Ananya Singh',
        member_5: 'Kabir Gupta',
        member_6: 'Isha Mishra',
        ref_1: 'HOS4-2026-001-1',
        ref_2: 'HOS4-2026-001-2',
        ref_3: 'HOS4-2026-001-3',
        ref_4: 'HOS4-2026-001-4',
        ref_5: 'HOS4-2026-001-5',
        ref_6: 'HOS4-2026-001-6',
      };
      renderWithContext(mockTeam);
    } else {
      const teamContext: any = {
        team_name: currentTeam.team_name,
        leader_name: currentTeam.leader_name,
        leader_email: currentTeam.leader_email,
        team_id: currentTeam.team_identifier || currentTeam.team_id,
        event_name: 'Hack-O-Sprint 4.0 – SIH Internal Round 2026',
      };
      for (let i = 1; i <= 6; i++) {
        teamContext[`member_${i}`] =
          currentTeam.participant_names[i - 1] || `Member ${i}`;
        teamContext[`ref_${i}`] = currentTeam.ref_numbers[i - 1] || '';
      }
      renderWithContext(teamContext);
    }
  }, [subject, body, selectedPreviewTeamIndex, validationReport]);

  const renderWithContext = async (ctx: any) => {
    try {
      const res = await apiClient.previewTemplate(subject, body, ctx);
      setPreviewRendered({
        subject: res.rendered_subject,
        body: res.rendered_body,
        missing: res.missing_placeholders
      });
    } catch (e) {
      // fallback
    }
  };

  const insertPlaceholder = (tag: string) => {
    setBody(body + ` {{${tag}}}`);
  };

  const placeholders = [
    { tag: 'leader_name', desc: "Leader's full name" },
    { tag: 'team_name', desc: 'Team name from Excel' },
    { tag: 'event_name', desc: 'Event title' },
    { tag: 'team_id', desc: 'Team identifier code' },
    { tag: 'member_1', desc: 'Position 1 name' },
    { tag: 'member_2', desc: 'Position 2 name' },
    { tag: 'member_3', desc: 'Position 3 name' },
    { tag: 'member_4', desc: 'Position 4 name' },
    { tag: 'member_5', desc: 'Position 5 name' },
    { tag: 'member_6', desc: 'Position 6 name' },
    { tag: 'ref_1', desc: 'Cert Ref #1' },
    { tag: 'ref_2', desc: 'Cert Ref #2' },
    { tag: 'ref_6', desc: 'Cert Ref #6' },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Step Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Step 4: Email Composer & Templates</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Craft your personalized message with dynamic variables and configure global CC/BCC recipients.
          </p>
        </div>

        <button
          onClick={() => setActiveView('preview_test')}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors self-start sm:self-auto"
        >
          Proceed to Preview & Test
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Main Grid: Composer vs Live Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Editor & Controls */}
        <div className="space-y-5">
          {/* Template Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-slate-500" />
              <label className="text-xs font-semibold text-slate-700">Preset Template:</label>
              <select
                value={selectedTemplateId}
                onChange={(e) => handleSelectTemplate(e.target.value)}
                className="text-xs px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} {t.is_default ? '(Default)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="New template name..."
                value={newTemplateName}
                onChange={(e) => setNewTemplateName(e.target.value)}
                className="text-xs px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg w-36"
              />
              <button
                onClick={handleSaveAsTemplate}
                disabled={savingTemplate}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
              >
                <Save className="w-3.5 h-3.5" />
                Save As
              </button>
            </div>
          </div>

          {/* Subject Field */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Email Subject Line</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-hidden font-medium"
                required
              />
            </div>

            {/* Global CC and BCC */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Global CC (Visible to all recipients)
                </label>
                <input
                  type="text"
                  placeholder="mentor@univ.edu, faculty@univ.edu"
                  value={globalCc}
                  onChange={(e) => setGlobalCc(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Included visibly on every team's email.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Global BCC (Hidden from leaders)
                </label>
                <input
                  type="text"
                  placeholder="archives@univ.edu"
                  value={globalBcc}
                  onChange={(e) => setGlobalBcc(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:ring-2 focus:ring-indigo-500"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Delivered silently without showing in To/CC.
                </span>
              </div>
            </div>

            {/* Email Message Body */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-bold text-slate-700">Message Body</label>
                <span className="text-[11px] text-slate-400">Plain text + auto HTML formatting</span>
              </div>
              <textarea
                rows={12}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="w-full p-3.5 text-xs sm:text-sm bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-hidden font-sans leading-relaxed"
                required
              />
            </div>

            {/* Clickable Placeholder Palette */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-2">
                Click to Insert Variable:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {placeholders.map((p) => (
                  <button
                    key={p.tag}
                    type="button"
                    onClick={() => insertPlaceholder(p.tag)}
                    title={p.desc}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-mono font-semibold rounded-lg border border-indigo-200 transition-colors"
                  >
                    <span>{`{{${p.tag}}}`}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Live Rendered Preview */}
        <div className="space-y-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">Live Team Sample Preview</h3>
              </div>

              {teams.length > 0 && (
                <div className="flex items-center gap-2">
                  <label className="text-xs text-slate-500">Sample Team:</label>
                  <select
                    value={selectedPreviewTeamIndex}
                    onChange={(e) => setSelectedPreviewTeamIndex(parseInt(e.target.value))}
                    className="text-xs px-2 py-1 bg-slate-50 border border-slate-300 rounded font-medium max-w-[180px] truncate"
                  >
                    {teams.map((t, idx) => (
                      <option key={t.team_id} value={idx}>
                        #{t.row_index}: {t.team_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Preview Email Container */}
            <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs">
              {/* Fake Email Client Header */}
              <div className="p-4 bg-slate-50/80 border-b border-slate-200 space-y-2 text-xs">
                <div>
                  <span className="font-semibold text-slate-500 w-16 inline-block">Subject:</span>
                  <span className="font-bold text-slate-900">{previewRendered.subject}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-500 w-16 inline-block">To:</span>
                  <span className="text-slate-800 font-mono">
                    {currentTeam ? `${currentTeam.leader_name} <${currentTeam.leader_email}>` : 'Aarav Sharma <aarav.sharma@example.com>'}
                  </span>
                </div>
                {globalCc && (
                  <div>
                    <span className="font-semibold text-slate-500 w-16 inline-block">CC:</span>
                    <span className="text-slate-600 font-mono">{globalCc}</span>
                  </div>
                )}
                {globalBcc && (
                  <div>
                    <span className="font-semibold text-slate-500 w-16 inline-block">BCC:</span>
                    <span className="text-slate-400 font-mono">{globalBcc} (Hidden)</span>
                  </div>
                )}
                <div className="pt-1 flex items-center gap-2 text-slate-500">
                  <span className="font-semibold w-16 inline-block">Attachments:</span>
                  <span className="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                    6 Participation Certificates (.png)
                  </span>
                </div>
              </div>

              {/* Fake Email Body */}
              <div className="p-6 text-sm text-slate-800 font-sans leading-relaxed whitespace-pre-line min-h-[260px] bg-white">
                {previewRendered.body}
              </div>
            </div>

            {/* Validation warnings if missing placeholders */}
            {previewRendered.missing.length > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  Unmatched variable placeholders detected: <code>{previewRendered.missing.join(', ')}</code>
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
