import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  ExcelUploadResponse,
  ZipBatchInfo,
  ValidationReportResponse,
  TeamMappingItem,
  apiClient
} from '../api/client';

export type ViewType =
  | 'overview'
  | 'upload'
  | 'mapping'
  | 'composer'
  | 'preview_test'
  | 'send'
  | 'recovery'
  | 'logs'
  | 'settings';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
}

interface AppContextType {
  activeView: ViewType;
  setActiveView: (view: ViewType) => void;
  sessionId: string;
  setSessionId: (id: string) => void;
  excelData: ExcelUploadResponse | null;
  setExcelData: (data: ExcelUploadResponse | null) => void;
  batches: ZipBatchInfo[];
  setBatches: React.Dispatch<React.SetStateAction<ZipBatchInfo[]>>;
  validationReport: ValidationReportResponse | null;
  setValidationReport: (report: ValidationReportResponse | null) => void;
  selectedTeam: TeamMappingItem | null;
  setSelectedTeam: (team: TeamMappingItem | null) => void;
  activeCampaignId: string | null;
  setActiveCampaignId: (id: string | null) => void;
  composedSubject: string;
  setComposedSubject: (subject: string) => void;
  composedBody: string;
  setComposedBody: (body: string) => void;
  globalCc: string;
  setGlobalCc: (cc: string) => void;
  globalBcc: string;
  setGlobalBcc: (bcc: string) => void;
  toasts: ToastMessage[];
  addToast: (type: 'success' | 'error' | 'info' | 'warning', title: string, message?: string) => void;
  removeToast: (id: string) => void;
  refreshStats: () => Promise<void>;
  overviewStats: any;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeView, setActiveView] = useState<ViewType>('overview');
  const [sessionId, setSessionIdState] = useState<string>(() => {
    return localStorage.getItem('certimailer_session_id') || ('session-' + Date.now());
  });

  const setSessionId = (id: string) => {
    localStorage.setItem('certimailer_session_id', id);
    setSessionIdState(id);
  };

  const [excelData, setExcelData] = useState<ExcelUploadResponse | null>(null);
  const [batches, setBatches] = useState<ZipBatchInfo[]>([]);
  const [validationReport, setValidationReport] = useState<ValidationReportResponse | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<TeamMappingItem | null>(null);
  const [activeCampaignId, setActiveCampaignId] = useState<string | null>(null);
  
  // Persisted email composer state to guarantee template consistency across Preview, Test & Dispatch
  const [composedSubject, setComposedSubject] = useState<string>(
    'Congratulations on Your Selection Among the Top Teams | Hack-O-Sprint 4.0'
  );
  const [composedBody, setComposedBody] = useState<string>(
    `Dear {{leader_name}},

Congratulations to you and your entire team, {{team_name}}, on being selected among the Top Teams in Hack-O-Sprint 4.0 – SIH Internal Round 2026, organized by the IEEE Student Branch and IEEE Computer Society Student Branch Chapter, IIIT Bhopal.

Your selection reflects your team's effort, creativity, and commitment to developing innovative solutions. We appreciate your participation and wish all six team members the very best for the next stages of the Smart India Hackathon journey.

Please find attached the participation certificates for all six members of your team.

Congratulations once again, and best wishes for your future endeavours!

Regards,  
IEEE Student Branch & IEEE Computer Society SBC  
Indian Institute of Information Technology, Bhopal`
  );
  const [globalCc, setGlobalCc] = useState<string>('');
  const [globalBcc, setGlobalBcc] = useState<string>('');

  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [overviewStats, setOverviewStats] = useState<any>(null);

  const addToast = (type: 'success' | 'error' | 'info' | 'warning', title: string, message?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const refreshStats = async () => {
    try {
      const stats = await apiClient.getOverviewStats();
      setOverviewStats(stats);
    } catch (e) {
      // silently ignore initial stats fetch
    }
  };

  useEffect(() => {
    refreshStats();
  }, [validationReport, activeCampaignId]);

  return (
    <AppContext.Provider
      value={{
        activeView,
        setActiveView,
        sessionId,
        setSessionId,
        excelData,
        setExcelData,
        batches,
        setBatches,
        validationReport,
        setValidationReport,
        selectedTeam,
        setSelectedTeam,
        activeCampaignId,
        setActiveCampaignId,
        composedSubject,
        setComposedSubject,
        composedBody,
        setComposedBody,
        globalCc,
        setGlobalCc,
        globalBcc,
        setGlobalBcc,
        toasts,
        addToast,
        removeToast,
        refreshStats,
        overviewStats
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within an AppProvider');
  return context;
};
