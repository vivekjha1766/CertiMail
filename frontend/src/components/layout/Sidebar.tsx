import React from 'react';
import {
  LayoutDashboard,
  UploadCloud,
  FileSpreadsheet,
  Mail,
  Eye,
  Send,
  RotateCcw,
  ScrollText,
  Settings,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useApp, ViewType } from '../../context/AppContext';

interface NavItem {
  id: ViewType;
  label: string;
  icon: React.ElementType;
  badge?: string | number;
  badgeColor?: string;
}

export const Sidebar: React.FC = () => {
  const { activeView, setActiveView, validationReport, excelData } = useApp();

  const navItems: NavItem[] = [
    { id: 'overview', label: '1. Overview', icon: LayoutDashboard },
    {
      id: 'upload',
      label: '2. Upload Files',
      icon: UploadCloud,
      badge: excelData ? `${excelData.row_count} rows` : undefined,
      badgeColor: 'bg-blue-100 text-blue-700'
    },
    {
      id: 'mapping',
      label: '3. Certificate Mapping',
      icon: FileSpreadsheet,
      badge: validationReport
        ? validationReport.summary.can_send
          ? 'Valid'
          : `${validationReport.summary.error_teams} err`
        : undefined,
      badgeColor: validationReport?.summary.can_send
        ? 'bg-emerald-100 text-emerald-700'
        : 'bg-rose-100 text-rose-700'
    },
    { id: 'composer', label: '4. Email Composer', icon: Mail },
    { id: 'preview_test', label: '5. Preview & Test', icon: Eye },
    { id: 'send', label: '6. Send Campaign', icon: Send },
    { id: 'recovery', label: 'Campaign Recovery', icon: RotateCcw },
    { id: 'logs', label: '7. Delivery Logs', icon: ScrollText },
    { id: 'settings', label: '8. Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between shrink-0 min-h-[calc(100vh-65px)]">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Workflow Steps
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-xs shadow-indigo-200'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${
                      isActive ? 'bg-white/20 text-white' : item.badgeColor
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Safety Notice Footer in Sidebar */}
      <div className="p-4 m-3 bg-slate-50 border border-slate-200 rounded-xl">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>Security Enforced</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
          Localhost only. SMTP secrets are kept in memory and never written to database or exposed in browser.
        </p>
      </div>
    </aside>
  );
};
