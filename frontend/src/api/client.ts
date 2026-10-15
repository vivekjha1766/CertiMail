import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 45000,
});

export interface ColumnSuggestions {
  team_name?: string;
  team_identifier?: string;
  leader_name?: string;
  leader_email?: string;
  participant_1?: string;
  participant_2?: string;
  participant_3?: string;
  participant_4?: string;
  participant_5?: string;
  participant_6?: string;
  ref_1?: string;
  ref_2?: string;
  ref_3?: string;
  ref_4?: string;
  ref_5?: string;
  ref_6?: string;
}

export interface ExcelUploadResponse {
  session_id: string;
  filename: string;
  sheets: string[];
  selected_sheet: string;
  detected_columns: string[];
  row_count: number;
  column_suggestions: ColumnSuggestions;
  sample_rows: Record<string, string>[];
}

export interface ZipBatchInfo {
  position: number;
  batch_id: string;
  filename: string;
  file_count: number;
  min_number?: number;
  max_number?: number;
  has_nested: boolean;
  warnings: string[];
}

export interface CertificateFileInfo {
  position: number;
  filename: string;
  relative_path: string;
  batch_name: string;
  exists: boolean;
  size_bytes: number;
  participant_name?: string;
  ref_number?: string;
}

export interface TeamMappingItem {
  team_id: string;
  row_index: number;
  team_name: string;
  team_identifier?: string;
  leader_name: string;
  leader_email: string;
  participant_names: string[];
  ref_numbers: string[];
  certificate_files: CertificateFileInfo[];
  validation_status: string;
  validation_errors: string[];
  manual_override: boolean;
  override_status?: string;
  override_reviewer?: string;
  override_reason?: string;
  override_timestamp?: string;
  detected_reference_mismatch?: string;
  custom_subject?: string;
  custom_body?: string;
  cc_recipients?: string;
  bcc_recipients?: string;
}

export interface MismatchAcknowledgement {
  policy: string;
  reviewer: string;
  reason: string;
  acknowledged_at: string;
  mismatches_count: number;
  unresolved_summary?: any[];
}

export interface ValidationSummary {
  total_teams: number;
  valid_teams: number;
  error_teams: number;
  duplicate_emails: number;
  missing_certificates: number;
  reference_mismatches: number;
  approved_overrides: number;
  total_certificates_detected: number;
  can_send: boolean;
  has_fatal_errors?: boolean;
  fatal_error_count?: number;
  can_proceed_with_current_mapping?: boolean;
  mismatch_acknowledgement?: MismatchAcknowledgement | null;
}


export interface ValidationReportResponse {
  summary: ValidationSummary;
  teams: TeamMappingItem[];
  batches: ZipBatchInfo[];
}

export interface TemplateItem {
  id: string;
  name: string;
  subject: string;
  body: string;
  is_default: boolean;
  created_at: string;
}

export interface SMTPConfig {
  host: string;
  port: number;
  use_tls: boolean;
  use_ssl: boolean;
  sender_name: string;
  sender_email: string;
  username: string;
  has_password: boolean;
  password?: string;
  global_cc?: string;
  global_bcc?: string;
}

export interface CampaignStatus {
  campaign_id: string;
  status: string;
  campaign_type?: string;
  total_teams: number;
  sent_count: number;
  failed_count: number;
  pending_count: number;
  uncertain_count?: number;
  progress_percent: number;
  current_team?: string;
  current_template_revision?: number;
  is_paused: boolean;
  is_completed: boolean;
  error_message?: string;
}

export interface TemplateRevision {
  id: string;
  campaign_id: string;
  revision_number: number;
  subject: string;
  body: string;
  global_cc: string;
  global_bcc: string;
  created_by: string;
  change_summary: string;
  is_active: boolean;
  created_at: string;
}

export interface CampaignRecipientItem {
  id: string;
  recipient_id: string;
  row_index: number;
  team_name: string;
  team_identifier?: string;
  leader_name: string;
  leader_email: string;
  normalized_email: string;
  delivery_status: string; // PENDING, IN_PROGRESS, SMTP_ACCEPTED, FAILED, DELIVERY_UNKNOWN, SKIPPED
  delivery_attempts: number;
  last_error?: string;
  template_revision_used: number;
  delivery_timestamp?: string;
  retry_authorized: boolean;
  certificate_count: number;
  certificate_names: string[];
}

export interface CampaignDetailResponse {
  campaign: {
    id: string;
    name: string;
    status: string;
    campaign_type: string;
    total_teams: number;
    sent_count: number;
    failed_count: number;
    pending_count: number;
    uncertain_count: number;
    total_certificates: number;
    estimated_size_mb: number;
    current_template_revision: number;
    is_paused: boolean;
    created_at: string;
  };
  revisions: TemplateRevision[];
  recipients: CampaignRecipientItem[];
  audit_logs: any[];
  summary_counts: {
    total: number;
    accepted: number;
    pending: number;
    failed: number;
    uncertain: number;
    skipped: number;
  };
}

export interface CampaignRecoveryItem {
  id: string;
  name: string;
  campaign_type: string;
  status: string;
  total_recipients: number;
  accepted_count: number;
  pending_count: number;
  failed_count: number;
  uncertain_count: number;
  remaining_count: number;
  current_template_revision: number;
  last_activity: string;
  is_resumable: boolean;
}

export interface TestSendResponse {
  success: boolean;
  message: string;
  actual_recipient: string;
  real_leader_email_protected: string;
  attachment_count: number;
  attachment_names: string[];
}

export interface DeliveryLogItem {
  id: string;
  campaign_id: string;
  team_id?: string;
  team_name?: string;
  recipient_email: string;
  cc_recipients?: string;
  bcc_count: number;
  attachment_count: number;
  attachment_names: string[];
  status: string;
  error_message?: string;
  retry_count: number;
  is_test: boolean;
  created_at: string;
}

export const apiClient = {
  // Uploads
  uploadExcel: async (file: File, sessionId?: string, sheetName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (sessionId) formData.append('session_id', sessionId);
    if (sheetName) formData.append('sheet_name', sheetName);
    const res = await api.post<ExcelUploadResponse>('/uploads/excel', formData);
    return res.data;
  },

  uploadCertificatesZip: async (file: File, sessionId: string, position: number) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    formData.append('position', position.toString());
    const res = await api.post<ZipBatchInfo>('/uploads/certificates', formData);
    return res.data;
  },

  getBatches: async (sessionId: string) => {
    const res = await api.get<ZipBatchInfo[]>(`/uploads/batches/${sessionId}`);
    return res.data;
  },

  // Mapping
  validateMapping: async (sessionId: string, columnMapping: any, offset = 0, selectedSheet?: string) => {
    const res = await api.post<ValidationReportResponse>('/mapping/validate', {
      session_id: sessionId,
      column_mapping: columnMapping,
      numbering_offset: offset,
      selected_sheet: selectedSheet
    });
    return res.data;
  },

  submitOverride: async (payload: any) => {
    const res = await api.post<ValidationReportResponse>('/mapping/override', payload);
    return res.data;
  },

  acknowledgeMismatches: async (sessionId: string, reviewer: string, reason: string, confirmed: boolean = true) => {
    const res = await api.post<ValidationReportResponse>('/mapping/acknowledge-mismatches', {
      session_id: sessionId,
      reviewer,
      reason,
      confirmed
    });
    return res.data;
  },

  resetMismatchAcknowledgement: async (sessionId: string) => {
    const res = await api.post<ValidationReportResponse>('/mapping/reset-mismatches', {
      session_id: sessionId
    });
    return res.data;
  },

  getReportDownloadUrl: (sessionId: string) => `/api/mapping/report/${sessionId}`,

  // Templates
  getTemplates: async () => {
    const res = await api.get<TemplateItem[]>('/templates');
    return res.data;
  },

  createTemplate: async (template: { name: string; subject: string; body: string }) => {
    const res = await api.post<TemplateItem>('/templates', template);
    return res.data;
  },

  updateTemplate: async (id: string, template: { name: string; subject: string; body: string }) => {
    const res = await api.put<TemplateItem>(`/templates/${id}`, template);
    return res.data;
  },

  deleteTemplate: async (id: string) => {
    const res = await api.delete(`/templates/${id}`);
    return res.data;
  },

  previewTemplate: async (subject: string, body: string, teamData: any) => {
    const res = await api.post('/templates/preview', {
      subject,
      body,
      team_data: teamData
    });
    return res.data;
  },

  // SMTP
  getSmtpConfig: async () => {
    const res = await api.get<SMTPConfig>('/smtp/config');
    return res.data;
  },

  updateSmtpConfig: async (config: SMTPConfig) => {
    const res = await api.post<SMTPConfig>('/smtp/config', config);
    return res.data;
  },

  testSmtpConnection: async (payload: any) => {
    const res = await api.post('/smtp/test', payload);
    return res.data;
  },

  // Campaigns
  createCampaign: async (payload: any) => {
    const res = await api.post('/campaigns', payload);
    return res.data;
  },

  listCampaigns: async () => {
    const res = await api.get('/campaigns');
    return res.data;
  },

  sendTestEmail: async (payload: any) => {
    const res = await api.post('/campaigns/test-send', payload);
    return res.data;
  },

  startCampaign: async (campaignId: string, payload: any) => {
    const res = await api.post(`/campaigns/${campaignId}/send`, payload);
    return res.data;
  },

  pauseCampaign: async (campaignId: string) => {
    const res = await api.post(`/campaigns/${campaignId}/pause`);
    return res.data;
  },

  resumeCampaign: async (campaignId: string, payload?: any) => {
    const res = await api.post(`/campaigns/${campaignId}/resume`, payload || {});
    return res.data;
  },

  cancelCampaign: async (campaignId: string) => {
    const res = await api.post(`/campaigns/${campaignId}/cancel`);
    return res.data;
  },

  getCampaignStatus: async (campaignId: string) => {
    const res = await api.get<CampaignStatus>(`/campaigns/${campaignId}/status`);
    return res.data;
  },

  getRecoverableCampaigns: async () => {
    const res = await api.get<CampaignRecoveryItem[]>('/campaigns/recovery');
    return res.data;
  },

  getCampaignDetail: async (campaignId: string) => {
    const res = await api.get<CampaignDetailResponse>(`/campaigns/${campaignId}`);
    return res.data;
  },

  updateCampaignTemplate: async (campaignId: string, payload: {
    choice: 'OPTION_A_KEEP_ORIGINAL' | 'OPTION_B_APPLY_TO_REMAINING';
    subject: string;
    body: string;
    global_cc?: string;
    global_bcc?: string;
    reviewer?: string;
    reason?: string;
  }) => {
    const res = await api.post(`/campaigns/${campaignId}/template`, payload);
    return res.data;
  },

  resolveUncertainDelivery: async (campaignId: string, payload: {
    recipient_id: string;
    action: 'authorize_retry' | 'mark_accepted' | 'mark_skipped';
    reviewer?: string;
    reason?: string;
  }) => {
    const res = await api.post(`/campaigns/${campaignId}/resolve-uncertain`, payload);
    return res.data;
  },

  retryFailedRecipients: async (campaignId: string, payload: {
    reviewer?: string;
    reason?: string;
  }) => {
    const res = await api.post(`/campaigns/${campaignId}/retry-failed`, payload);
    return res.data;
  },

  // Logs & Stats
  getDeliveryLogs: async (params?: any) => {
    const res = await api.get<{ total: number; items: DeliveryLogItem[] }>('/logs', { params });
    return res.data;
  },

  getOverviewStats: async () => {
    const res = await api.get('/logs/stats');
    return res.data;
  },

  getExportLogsUrl: (type: string, campaignId?: string) => {
    let url = `/api/logs/export/${type}`;
    if (campaignId) url += `?campaign_id=${campaignId}`;
    return url;
  },

  // Image URLs
  getThumbnailUrl: (batchId: string, filename: string) => `/api/certificates/thumbnail/${batchId}/${filename}`,
  getFullImageUrl: (batchId: string, filename: string) => `/api/certificates/full/${batchId}/${filename}`,
};
