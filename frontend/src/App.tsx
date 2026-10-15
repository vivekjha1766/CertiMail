import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { OverviewView } from './views/OverviewView';
import { UploadView } from './views/UploadView';
import { MappingView } from './views/MappingView';
import { ComposerView } from './views/ComposerView';
import { PreviewTestView } from './views/PreviewTestView';
import { SendCampaignView } from './views/SendCampaignView';
import { RecoveryView } from './views/RecoveryView';
import { DeliveryLogsView } from './views/DeliveryLogsView';
import { SettingsView } from './views/SettingsView';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

const MainContent: React.FC = () => {
  const { activeView, toasts, removeToast } = useApp();

  const renderActiveView = () => {
    switch (activeView) {
      case 'overview':
        return <OverviewView />;
      case 'upload':
        return <UploadView />;
      case 'mapping':
        return <MappingView />;
      case 'composer':
        return <ComposerView />;
      case 'preview_test':
        return <PreviewTestView />;
      case 'send':
        return <SendCampaignView />;
      case 'recovery':
        return <RecoveryView />;
      case 'logs':
        return <DeliveryLogsView />;
      case 'settings':
        return <SettingsView />;
      default:
        return <OverviewView />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 sm:p-8 overflow-y-auto">
          {renderActiveView()}
        </main>
      </div>

      {/* Floating Toast Notification Stack */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => {
          const isSuccess = toast.type === 'success';
          const isError = toast.type === 'error';
          const isWarning = toast.type === 'warning';
          return (
            <div
              key={toast.id}
              className={`pointer-events-auto p-4 rounded-xl shadow-lg border flex items-start gap-3 transition-all ${
                isSuccess
                  ? 'bg-white border-emerald-200 text-slate-800'
                  : isError
                  ? 'bg-white border-rose-200 text-slate-800'
                  : isWarning
                  ? 'bg-white border-amber-200 text-slate-800'
                  : 'bg-white border-slate-200 text-slate-800'
              }`}
            >
              {isSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />}
              {isError && <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />}
              {isWarning && <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />}
              {toast.type === 'info' && <Info className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />}

              <div className="flex-1 min-w-0">
                <h4 className="text-xs font-bold">{toast.title}</h4>
                {toast.message && (
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{toast.message}</p>
                )}
              </div>

              <button
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-slate-700 p-0.5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default function App() {
  return (
    <AppProvider>
      <MainContent />
    </AppProvider>
  );
}
