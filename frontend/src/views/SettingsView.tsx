import React, { useState, useEffect } from 'react';
import {
  Settings,
  Mail,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  HelpCircle,
  ExternalLink,
  Save,
  Server
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient, SMTPConfig } from '../api/client';

export const SettingsView: React.FC = () => {
  const { addToast } = useApp();

  const [host, setHost] = useState('smtp.gmail.com');
  const [port, setPort] = useState(587);
  const [useTls, setUseTls] = useState(true);
  const [useSsl, setUseSsl] = useState(false);
  const [senderName, setSenderName] = useState('Hack-O-Sprint 4.0 Organizing Team');
  const [senderEmail, setSenderEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [hasExistingPassword, setHasExistingPassword] = useState(false);

  const [testingConnection, setTestingConnection] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    details?: string;
  } | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const cfg = await apiClient.getSmtpConfig();
      setHost(cfg.host || 'smtp.gmail.com');
      setPort(cfg.port || 587);
      setUseTls(cfg.use_tls !== undefined ? cfg.use_tls : true);
      setUseSsl(cfg.use_ssl || false);
      setSenderName(cfg.sender_name || 'Hack-O-Sprint 4.0 Organizing Team');
      setSenderEmail(cfg.sender_email || '');
      setUsername(cfg.username || '');
      setHasExistingPassword(cfg.has_password);
    } catch (e) {
      // ignore
    }
  };

  const applyGmailPreset = () => {
    setHost('smtp.gmail.com');
    setPort(587);
    setUseTls(true);
    setUseSsl(false);
    addToast('info', 'Gmail Preset Applied', 'Host: smtp.gmail.com, Port: 587, Security: STARTTLS');
  };

  const handleTestConnection = async () => {
    if (!username.trim()) {
      addToast('warning', 'Username Required', 'Please enter your SMTP username (e.g. your Gmail address).');
      return;
    }
    if (!password && !hasExistingPassword) {
      addToast('warning', 'Password Required', 'Please enter your SMTP App Password.');
      return;
    }

    setTestingConnection(true);
    setTestResult(null);

    try {
      const res = await apiClient.testSmtpConnection({
        host,
        port,
        use_tls: useTls,
        use_ssl: useSsl,
        username: username.trim(),
        password: password
      });

      setTestResult(res);
      if (res.success) {
        addToast('success', 'SMTP Connected', res.message);
      } else {
        addToast('error', 'SMTP Authentication Failed', res.message);
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.response?.data?.detail || err.message,
        details: err.message
      });
      addToast('error', 'Connection Error', err.response?.data?.detail || err.message);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      await apiClient.updateSmtpConfig({
        host,
        port,
        use_tls: useTls,
        use_ssl: useSsl,
        sender_name: senderName,
        sender_email: senderEmail || username,
        username: username.trim(),
        has_password: Boolean(password || hasExistingPassword),
        password: password || undefined
      });

      if (password) {
        setHasExistingPassword(true);
      }
      addToast('success', 'Settings Saved', 'SMTP configuration updated in backend memory.');
    } catch (err: any) {
      addToast('error', 'Save Failed', err.response?.data?.detail || err.message);
    } finally {
      setSavingSettings(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Step 8: SMTP Configuration & Security</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Configure authenticated mail server credentials with strict in-memory security and TLS verification.
        </p>
      </div>

      {/* Main Settings Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Outgoing Mail Server (SMTP)</h3>
              <p className="text-xs text-slate-500">Supports Gmail, Google Workspace, Outlook, and Custom SMTP servers.</p>
            </div>
          </div>

          <button
            type="button"
            onClick={applyGmailPreset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-lg border border-indigo-200 transition-colors"
          >
            Apply Gmail Preset (587 STARTTLS)
          </button>
        </div>

        <form onSubmit={handleSaveConfig} className="space-y-4">
          {/* Host & Port */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">SMTP Hostname</label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Port</label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(parseInt(e.target.value) || 587)}
                className="w-full px-3 py-2 text-xs font-mono bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
          </div>

          {/* Security Protocols */}
          <div className="flex items-center gap-6 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
            <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={useTls}
                onChange={(e) => setUseTls(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Enable STARTTLS (Port 587 - Recommended)
            </label>

            <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={useSsl}
                onChange={(e) => setUseSsl(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Enable SSL (Port 465)
            </label>
          </div>

          {/* Sender Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Sender Display Name</label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Sender Email Address</label>
              <input
                type="email"
                placeholder="event@organization.org"
                value={senderEmail}
                onChange={(e) => setSenderEmail(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Credentials */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                SMTP Username (Email) <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                placeholder="your-gmail@gmail.com"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 text-xs font-medium bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                SMTP App Password <span className="text-rose-500">*</span>
              </label>
              <input
                type="password"
                placeholder={hasExistingPassword ? '•••••••••••••••• (Stored in memory)' : '16-character App Password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 text-xs font-mono bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testingConnection}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl transition-colors shadow-2xs"
            >
              <ShieldCheck className="w-4 h-4 text-slate-600" />
              {testingConnection ? 'Testing Authentication...' : 'Test SMTP Connection'}
            </button>

            <button
              type="submit"
              disabled={savingSettings}
              className="inline-flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition-colors shadow-xs"
            >
              <Save className="w-4 h-4" />
              {savingSettings ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>

        {/* Test Result Feedback */}
        {testResult && (
          <div
            className={`p-4 rounded-xl border text-xs space-y-1.5 ${
              testResult.success
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            <div className="font-bold flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-600" />
              )}
              {testResult.message}
            </div>
            {testResult.details && (
              <p className="font-mono text-[11px] text-rose-700 mt-1 leading-relaxed">
                {testResult.details}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Security Guidance Guide */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
        <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-indigo-600" />
          How to Generate a Gmail App Password
        </h4>
        <ol className="list-decimal pl-5 text-xs text-slate-600 space-y-1.5 leading-relaxed">
          <li>
            Go to your <strong>Google Account</strong> (myaccount.google.com) and navigate to <strong>Security</strong>.
          </li>
          <li>
            Ensure <strong>2-Step Verification</strong> is turned ON for your account.
          </li>
          <li>
            Search for <strong>"App passwords"</strong> in the security search box.
          </li>
          <li>
            Create a new app named <strong>"CertiMail"</strong> and copy the generated 16-character code (e.g. <code>abcd efgh ijkl mnop</code>).
          </li>
          <li>
            Paste the 16 characters into the <strong>SMTP App Password</strong> field above. Never share this code.
          </li>
        </ol>
      </div>
    </div>
  );
};
