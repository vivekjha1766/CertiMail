import React, { useEffect } from 'react';
import { X, ExternalLink, Download } from 'lucide-react';
import { CertificateFileInfo } from '../../api/client';

interface ImageLightboxModalProps {
  cert: CertificateFileInfo | null;
  onClose: () => void;
}

export const ImageLightboxModal: React.FC<ImageLightboxModalProps> = ({ cert, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!cert) return null;

  const imageUrl = `/api/certificates/full/${cert.batch_name.replace(' ', '_')}/${cert.filename}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4 sm:p-6">
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Certificate Preview: {cert.participant_name || `Member ${cert.position}`}
            </h3>
            <p className="text-xs text-slate-500 font-mono">
              {cert.filename} • {cert.batch_name} {cert.ref_number ? `• Ref: ${cert.ref_number}` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={imageUrl}
              target="_blank"
              rel="noreferrer"
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
              title="Open raw image in new tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
            <button
              onClick={onClose}
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Image Container */}
        <div className="flex-1 overflow-auto p-6 bg-slate-100 flex items-center justify-center min-h-[350px]">
          <img
            src={imageUrl}
            alt={cert.filename}
            className="max-h-[70vh] max-w-full object-contain rounded-lg shadow-md border border-slate-200"
            onError={(e) => {
              (e.target as HTMLImageElement).src =
                'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect fill="%23f1f5f9" width="400" height="300"/><text fill="%2364748b" font-family="sans-serif" font-size="14" x="50%" y="50%" dominant-baseline="middle" text-anchor="middle">Image preview unavailable</text></svg>';
            }}
          />
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-white flex justify-between items-center text-xs text-slate-500">
          <span>Position {cert.position} of 6 in team certificate package</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
