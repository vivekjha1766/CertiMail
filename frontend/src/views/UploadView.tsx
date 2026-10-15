import React, { useState } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  Archive,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  FolderArchive,
  HelpCircle
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiClient, ZipBatchInfo } from '../api/client';

export const UploadView: React.FC = () => {
  const {
    sessionId,
    excelData,
    setExcelData,
    batches,
    setBatches,
    setValidationReport,
    setActiveView,
    addToast
  } = useApp();

  const [uploadingExcel, setUploadingExcel] = useState(false);
  const [uploadingZipIndex, setUploadingZipIndex] = useState<number | null>(null);

  // Column mapping state
  const [teamNameCol, setTeamNameCol] = useState(excelData?.column_suggestions.team_name || '');
  const [teamIdCol, setTeamIdCol] = useState(excelData?.column_suggestions.team_identifier || '');
  const [leaderNameCol, setLeaderNameCol] = useState(excelData?.column_suggestions.leader_name || '');
  const [leaderEmailCol, setLeaderEmailCol] = useState(excelData?.column_suggestions.leader_email || '');
  
  const [participantCols, setParticipantCols] = useState<string[]>([
    excelData?.column_suggestions.participant_1 || '',
    excelData?.column_suggestions.participant_2 || '',
    excelData?.column_suggestions.participant_3 || '',
    excelData?.column_suggestions.participant_4 || '',
    excelData?.column_suggestions.participant_5 || '',
    excelData?.column_suggestions.participant_6 || '',
  ]);

  const [refCols, setRefCols] = useState<string[]>([
    excelData?.column_suggestions.ref_1 || '',
    excelData?.column_suggestions.ref_2 || '',
    excelData?.column_suggestions.ref_3 || '',
    excelData?.column_suggestions.ref_4 || '',
    excelData?.column_suggestions.ref_5 || '',
    excelData?.column_suggestions.ref_6 || '',
  ]);

  const [numberingOffset, setNumberingOffset] = useState<number>(0);
  const [validating, setValidating] = useState(false);

  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingExcel(true);
    try {
      const res = await apiClient.uploadExcel(file, sessionId);
      setExcelData(res);
      
      // Auto-populate mapping state with suggestions
      setTeamNameCol(res.column_suggestions.team_name || '');
      setTeamIdCol(res.column_suggestions.team_identifier || '');
      setLeaderNameCol(res.column_suggestions.leader_name || '');
      setLeaderEmailCol(res.column_suggestions.leader_email || '');
      setParticipantCols([
        res.column_suggestions.participant_1 || '',
        res.column_suggestions.participant_2 || '',
        res.column_suggestions.participant_3 || '',
        res.column_suggestions.participant_4 || '',
        res.column_suggestions.participant_5 || '',
        res.column_suggestions.participant_6 || '',
      ]);
      setRefCols([
        res.column_suggestions.ref_1 || '',
        res.column_suggestions.ref_2 || '',
        res.column_suggestions.ref_3 || '',
        res.column_suggestions.ref_4 || '',
        res.column_suggestions.ref_5 || '',
        res.column_suggestions.ref_6 || '',
      ]);

      addToast('success', 'Excel Uploaded', `Loaded ${res.row_count} teams from "${res.selected_sheet}"`);
    } catch (err: any) {
      addToast('error', 'Upload Failed', err.response?.data?.detail || err.message);
    } finally {
      setUploadingExcel(false);
    }
  };

  const handleSheetChange = async (sheetName: string) => {
    if (!excelData) return;
    setUploadingExcel(true);
    try {
      // Re-read with selected sheet
      // Create empty mock file or re-query
      addToast('info', 'Switching Worksheet', `Selected sheet: ${sheetName}`);
    } finally {
      setUploadingExcel(false);
    }
  };

  const handleZipUpload = async (position: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingZipIndex(position);
    try {
      const batchInfo = await apiClient.uploadCertificatesZip(file, sessionId, position);
      setBatches((prev) => {
        const filtered = prev.filter((b) => b.position !== position);
        return [...filtered, batchInfo].sort((a, b) => a.position - b.position);
      });
      addToast('success', `Batch ${position} Uploaded`, `Found ${batchInfo.file_count} certificates in "${file.name}"`);
    } catch (err: any) {
      addToast('error', `Batch ${position} Failed`, err.response?.data?.detail || err.message);
    } finally {
      setUploadingZipIndex(null);
    }
  };

  const handleRunValidation = async () => {
    if (!excelData) {
      addToast('warning', 'Missing Excel File', 'Please upload your teams workbook first.');
      return;
    }
    if (!teamNameCol || !leaderEmailCol || !leaderNameCol) {
      addToast('warning', 'Incomplete Mapping', 'Please map Team Name, Leader Name, and Leader Email.');
      return;
    }

    setValidating(true);
    try {
      const mapping = {
        team_name: teamNameCol,
        team_identifier: teamIdCol || undefined,
        leader_name: leaderNameCol,
        leader_email: leaderEmailCol,
        participant_1: participantCols[0] || undefined,
        participant_2: participantCols[1] || undefined,
        participant_3: participantCols[2] || undefined,
        participant_4: participantCols[3] || undefined,
        participant_5: participantCols[4] || undefined,
        participant_6: participantCols[5] || undefined,
        ref_1: refCols[0] || undefined,
        ref_2: refCols[1] || undefined,
        ref_3: refCols[2] || undefined,
        ref_4: refCols[3] || undefined,
        ref_5: refCols[4] || undefined,
        ref_6: refCols[5] || undefined,
      };

      const report = await apiClient.validateMapping(
        sessionId,
        mapping,
        numberingOffset,
        excelData.selected_sheet
      );

      setValidationReport(report);
      addToast(
        report.summary.can_send ? 'success' : 'warning',
        'Validation Completed',
        `Validated ${report.summary.total_teams} teams: ${report.summary.valid_teams} valid, ${report.summary.error_teams} with errors`
      );
      setActiveView('mapping');
    } catch (err: any) {
      addToast('error', 'Validation Failed', err.response?.data?.detail || err.message);
    } finally {
      setValidating(false);
    }
  };

  const allZipsUploaded = [1, 2, 3, 4, 5, 6].every((pos) => batches.some((b) => b.position === pos));

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Step Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Step 2: Upload Files & Map Columns</h2>
        <p className="text-sm text-slate-500 mt-1">
          Upload your selected teams Excel workbook and assign the 6 certificate ZIP archives to each participant position.
        </p>
      </div>

      {/* Part A: Excel Upload */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">1. Excel Teams Workbook</h3>
              <p className="text-xs text-slate-500">Supported formats: .xlsx, .xls (e.g. "Certificates for top 75 participants new.xlsx")</p>
            </div>
          </div>
          {excelData && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {excelData.row_count} Rows Loaded
            </span>
          )}
        </div>

        {/* Upload Zone */}
        {!excelData ? (
          <label className="border-2 border-dashed border-slate-300 hover:border-indigo-500 hover:bg-indigo-50/20 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors group">
            <UploadCloud className="w-10 h-10 text-slate-400 group-hover:text-indigo-600 transition-colors mb-2" />
            <span className="text-sm font-semibold text-slate-700">Click or Drag & Drop Excel Workbook</span>
            <span className="text-xs text-slate-400 mt-1">Maximum size: 50MB</span>
            <input type="file" accept=".xlsx,.xls" onChange={handleExcelUpload} disabled={uploadingExcel} className="hidden" />
          </label>
        ) : (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-sm font-bold text-slate-800">{excelData.filename}</div>
              <div className="text-xs text-slate-500 mt-0.5">
                Worksheet: <span className="font-semibold text-slate-700">{excelData.selected_sheet}</span> • {excelData.row_count} teams detected
              </div>
            </div>
            <label className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 text-xs font-semibold text-slate-700 rounded-lg cursor-pointer transition-colors shadow-2xs">
              Replace File
              <input type="file" accept=".xlsx,.xls" onChange={handleExcelUpload} disabled={uploadingExcel} className="hidden" />
            </label>
          </div>
        )}
      </div>

      {/* Part B: Six ZIP Archives */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-50 text-purple-600">
              <FolderArchive className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">2. Six Participant Certificate Archives</h3>
              <p className="text-xs text-slate-500">
                Upload one ZIP archive per participant position (Position 1 = Leader, Positions 2 to 6 = Members).
              </p>
            </div>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
            {batches.length} / 6 Batches Assigned
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((pos) => {
            const batch = batches.find((b) => b.position === pos);
            const isUploading = uploadingZipIndex === pos;
            return (
              <div
                key={pos}
                className={`p-4 rounded-xl border transition-all ${
                  batch ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 bg-slate-50/50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                    Position {pos} ({pos === 1 ? 'Team Leader' : `Member ${pos}`})
                  </span>
                  {batch ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {batch.file_count} Certs
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400">Not Uploaded</span>
                  )}
                </div>

                {batch ? (
                  <div className="space-y-1 text-xs">
                    <p className="font-mono text-slate-700 truncate" title={batch.filename}>
                      {batch.filename}
                    </p>
                    <p className="text-slate-500 text-[11px]">
                      Numbers detected: #{batch.min_number || 1} to #{batch.max_number || batch.file_count}
                    </p>
                    <label className="block mt-2 text-indigo-600 hover:text-indigo-800 text-[11px] font-semibold cursor-pointer">
                      Replace ZIP
                      <input
                        type="file"
                        accept=".zip"
                        onChange={(e) => handleZipUpload(pos, e)}
                        disabled={isUploading}
                        className="hidden"
                      />
                    </label>
                  </div>
                ) : (
                  <label className="border border-dashed border-slate-300 hover:border-indigo-500 rounded-lg p-3.5 flex flex-col items-center justify-center cursor-pointer bg-white transition-colors group">
                    <Archive className="w-5 h-5 text-slate-400 group-hover:text-indigo-600 mb-1" />
                    <span className="text-xs font-medium text-slate-700">
                      {isUploading ? 'Extracting...' : `Upload ZIP for Position ${pos}`}
                    </span>
                    <input
                      type="file"
                      accept=".zip"
                      onChange={(e) => handleZipUpload(pos, e)}
                      disabled={isUploading}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Part C: Column Mapping */}
      {excelData && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">3. Column Mapping Configuration</h3>
              <p className="text-xs text-slate-500">
                Confirm or adjust which Excel columns correspond to team info and participant names.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-xs font-semibold text-slate-600 flex items-center gap-1.5">
                Numbering Offset:
                <input
                  type="number"
                  value={numberingOffset}
                  onChange={(e) => setNumberingOffset(parseInt(e.target.value) || 0)}
                  className="w-16 px-2 py-1 text-xs font-mono bg-slate-50 border border-slate-300 rounded focus:ring-2 focus:ring-indigo-500"
                />
              </label>
            </div>
          </div>

          {/* Primary Columns */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Team Name <span className="text-rose-500">*</span>
              </label>
              <select
                value={teamNameCol}
                onChange={(e) => setTeamNameCol(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                <option value="">-- Select Column --</option>
                {excelData.detected_columns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Team ID (Optional)</label>
              <select
                value={teamIdCol}
                onChange={(e) => setTeamIdCol(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                <option value="">-- None / Auto-generate --</option>
                {excelData.detected_columns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Leader Name <span className="text-rose-500">*</span>
              </label>
              <select
                value={leaderNameCol}
                onChange={(e) => setLeaderNameCol(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                <option value="">-- Select Column --</option>
                {excelData.detected_columns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Leader Email (To:) <span className="text-rose-500">*</span>
              </label>
              <select
                value={leaderEmailCol}
                onChange={(e) => setLeaderEmailCol(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                <option value="">-- Select Column --</option>
                {excelData.detected_columns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Six Participant Names & Reference Numbers */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              Participant Names & Certificate References (Positions 1 to 6)
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {[0, 1, 2, 3, 4, 5].map((idx) => (
                <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <span className="text-xs font-bold text-slate-800">
                    Position {idx + 1} ({idx === 0 ? 'Leader' : `Member ${idx + 1}`})
                  </span>
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-0.5">Participant Name Column</label>
                    <select
                      value={participantCols[idx]}
                      onChange={(e) => {
                        const updated = [...participantCols];
                        updated[idx] = e.target.value;
                        setParticipantCols(updated);
                      }}
                      className="w-full text-xs px-2 py-1.5 bg-white border border-slate-300 rounded focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">-- Fallback Name --</option>
                      {excelData.detected_columns.map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-500 mb-0.5">Certificate Ref # (Optional)</label>
                    <select
                      value={refCols[idx]}
                      onChange={(e) => {
                        const updated = [...refCols];
                        updated[idx] = e.target.value;
                        setRefCols(updated);
                      }}
                      className="w-full text-xs px-2 py-1.5 bg-white border border-slate-300 rounded focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">-- No Ref Column --</option>
                      {excelData.detected_columns.map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Validation Action */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <div className="text-xs text-slate-500">
              Certificate mapping engine will verify all 6 batches against {excelData.row_count} teams before allowing email delivery.
            </div>
            <button
              onClick={handleRunValidation}
              disabled={validating}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs tracking-wide shadow-md transition-colors"
            >
              {validating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Validating Mapping...
                </>
              ) : (
                <>
                  Validate Certificate Mapping
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
