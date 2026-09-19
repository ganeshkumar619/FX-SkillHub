import React, { useState, useEffect } from 'react';
import type { Certificate } from '../types';
import { Download, ExternalLink, X, Award, CheckCircle2, ShieldAlert } from 'lucide-react';
import { apiClient } from '../api/client';

interface CertificateBrandingConfig {
  institution_name: string;
  subtext: string;
  accreditation_text: string;
  signatory_1_title: string;
  signatory_1_name: string;
  signatory_2_title: string;
  signatory_2_name: string;
  watermark_enabled?: boolean;
  watermark_opacity?: number;
  horizontal_logo_url?: string;
  circular_emblem_url?: string;
  watermark_url?: string;
}

interface CertificatePreviewModalProps {
  certificate: Certificate | null;
  isOpen: boolean;
  onClose: () => void;
  studentNameFallback?: string;
}

export const CertificatePreviewModal: React.FC<CertificatePreviewModalProps> = ({
  certificate,
  isOpen,
  onClose,
  studentNameFallback = 'STUDENT'
}) => {
  const [brandingConfig, setBrandingConfig] = useState<CertificateBrandingConfig | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;
    apiClient.get<CertificateBrandingConfig>('/certificates/config/')
      .then((res) => {
        if (isMounted && res.data) {
          setBrandingConfig(res.data);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen || !certificate) return null;

  const institutionName = brandingConfig?.institution_name || 'FRANCIS XAVIER ENGINEERING COLLEGE';
  const subtext = brandingConfig?.subtext || '(Autonomous)';
  const accreditationText = brandingConfig?.accreditation_text ?? 'Approved by AICTE & Affiliated to Anna University';
  const fullSubtext = accreditationText ? `${subtext} • ${accreditationText}` : subtext;

  const sig1Title = brandingConfig?.signatory_1_title || 'Authorized Signatory';
  const sig1Name = brandingConfig?.signatory_1_name || 'Francis Xavier Engineering College';
  const sig2Title = brandingConfig?.signatory_2_title || 'Course Coordinator';
  const sig2Name = brandingConfig?.signatory_2_name || 'Centre for Skills Development';
  const isWatermarkEnabled = brandingConfig?.watermark_enabled ?? true;
  const watermarkOpacity = brandingConfig?.watermark_opacity ?? 0.06;
  const horizontalLogoUrl = brandingConfig?.horizontal_logo_url || '/fxec_logo.png';
  const emblemUrl = brandingConfig?.circular_emblem_url || '/fxec_crest.png';
  const watermarkUrl = brandingConfig?.watermark_url || '/fxec_crest.png';

  const certId = certificate.id || certificate.certificate_id || certificate.certificate_number;
  const certNumber = certificate.certificate_number || certId;
  const displayName = (certificate.student_name || studentNameFallback).toUpperCase();
  const displaySkill = certificate.skill || 'Engineering Specialization';
  const displayScore = certificate.score || certificate.assessment_score || '85 / 100';
  
  const issueDateFormatted = certificate.issue_date || (
    certificate.issued_at
      ? new Date(certificate.issued_at).toLocaleDateString('en-US', {
          day: 'numeric',
          month: 'long',
          year: 'numeric'
        }).toUpperCase()
      : '16 SEPTEMBER 2026'
  );

  const isRevoked = certificate.is_revoked || certificate.status === 'REVOKED';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-sm overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl bg-white rounded-3xl shadow-2xl overflow-hidden border border-slate-700 flex flex-col my-auto">
        
        {/* Top Control Bar */}
        <div className="bg-[#0b1e3d] text-white px-6 py-3.5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Award className="w-5 h-5 text-[#d4af37]" />
            <div>
              <h2 className="text-sm font-bold tracking-wide text-white">
                Official Credential Document Preview
              </h2>
              <p className="text-[11px] text-slate-300">
                Francis Xavier Engineering College (Autonomous) • High-Resolution A4 Landscape Render
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isRevoked ? (
              <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-rose-500/20 border border-rose-500/40 text-rose-300 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" /> Revoked
              </span>
            ) : (
              <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Verified Credential
              </span>
            )}
            
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              title="Close Preview"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Certificate Display Canvas (Landscape A4 matching PDF) */}
        <div className="p-4 sm:p-8 bg-slate-100 flex justify-center items-center overflow-x-auto">
          <div 
            className="relative w-full max-w-4xl bg-[#FDFAF7] text-slate-900 shadow-2xl rounded-sm p-6 sm:p-10 select-none overflow-hidden"
            style={{
              aspectRatio: '842 / 595',
              border: '4px solid #0b1e3d',
              outline: '1.5px solid #d4af37',
              outlineOffset: '-7px'
            }}
          >
            {/* Top-Right Multi-faceted Geometric Ribbon */}
            <div className="absolute top-0 right-0 w-44 sm:w-56 h-36 sm:h-44 pointer-events-none overflow-hidden">
              <svg viewBox="0 0 200 160" className="w-full h-full">
                <polygon points="0,0 200,160 200,0" fill="#e0f2fe" />
                <polygon points="50,0 200,130 200,60 110,0" fill="#38bdf8" />
                <polygon points="90,0 200,100 200,40 140,0" fill="#1d4ed8" />
                <polygon points="140,0 200,60 200,0" fill="#0b1e3d" />
                <line x1="0" y1="0" x2="200" y2="160" stroke="#d4af37" strokeWidth="2" />
              </svg>
            </div>

            {/* Bottom-Right Matching Ribbon */}
            <div className="absolute bottom-0 right-0 w-36 sm:w-44 h-28 sm:h-36 pointer-events-none overflow-hidden">
              <svg viewBox="0 0 160 130" className="w-full h-full">
                <polygon points="0,130 160,0 160,130" fill="#e0f2fe" />
                <polygon points="40,130 160,30 160,80 90,130" fill="#38bdf8" />
                <polygon points="100,130 160,80 160,130" fill="#0b1e3d" />
                <line x1="0" y1="130" x2="160" y2="0" stroke="#d4af37" strokeWidth="1.5" />
              </svg>
            </div>

            {/* Top-Left Corner Detail */}
            <div className="absolute top-0 left-0 w-16 h-16 pointer-events-none overflow-hidden">
              <svg viewBox="0 0 60 60" className="w-full h-full">
                <polygon points="0,0 0,60 60,0" fill="#0b1e3d" />
                <line x1="0" y1="60" x2="60" y2="0" stroke="#d4af37" strokeWidth="1.5" />
              </svg>
            </div>

            {/* Bottom-Left Corner Detail */}
            <div className="absolute bottom-0 left-0 w-14 h-14 pointer-events-none overflow-hidden">
              <svg viewBox="0 0 50 50" className="w-full h-full">
                <polygon points="0,50 50,50 0,0" fill="#0b1e3d" />
                <line x1="0" y1="0" x2="50" y2="50" stroke="#d4af37" strokeWidth="1.5" />
              </svg>
            </div>

            {/* Faint Center Institutional Watermark */}
            {isWatermarkEnabled && (
              <div 
                className="absolute inset-0 flex items-center justify-center pointer-events-none z-0"
                style={{ opacity: watermarkOpacity }}
              >
                <img
                  src={watermarkUrl}
                  alt="Watermark"
                  className="w-72 h-72 sm:w-96 sm:h-96 object-contain"
                />
              </div>
            )}

            {/* Top Institutional Header Row */}
            <div className="relative z-10 flex items-start justify-between gap-4 pb-3 sm:pb-5">
              {/* Left: Official Horizontal Logo */}
              <div className="w-48 sm:w-60 shrink-0">
                <img
                  src={horizontalLogoUrl}
                  alt="Francis Xavier Engineering College Logo"
                  className="h-10 sm:h-14 object-contain"
                  onError={(e) => {
                    // Fallback to text if missing
                    e.currentTarget.style.display = 'none';
                    const parent = e.currentTarget.parentElement;
                    if (parent) {
                      const div = document.createElement('div');
                      div.className = 'px-3 py-1.5 rounded border border-rose-300 bg-rose-50 text-[10px] font-bold text-rose-800';
                      div.innerText = 'OFFICIAL LOGO ASSET REQUIRED';
                      parent.appendChild(div);
                    }
                  }}
                />
              </div>

              {/* Center: Exact Prominent Institution Title */}
              <div className="text-center flex-1 px-2 hidden sm:block">
                <h1 className="text-sm sm:text-base font-extrabold text-[#0b1e3d] tracking-wider uppercase">
                  {institutionName}
                </h1>
                <p className="text-[10px] sm:text-xs text-slate-600 font-medium">
                  {fullSubtext}
                </p>
                <div className="w-48 h-[1px] bg-[#d4af37] mx-auto mt-1" />
              </div>

              {/* Right: Circular FXEC Emblem */}
              <div className="w-12 sm:w-16 h-12 sm:h-16 shrink-0 relative mr-4 sm:mr-6">
                <img
                  src={emblemUrl}
                  alt="FXEC Emblem"
                  className="w-full h-full object-contain rounded-full bg-white p-0.5 shadow-sm border border-slate-200"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                    const parent = e.currentTarget.parentElement;
                    if (parent) {
                      const div = document.createElement('div');
                      div.className = 'w-12 h-12 rounded-full border border-rose-300 bg-rose-50 flex items-center justify-center text-[7px] font-bold text-rose-800 text-center leading-tight';
                      div.innerText = 'OFFICIAL EMBLEM REQUIRED';
                      parent.appendChild(div);
                    }
                  }}
                />
              </div>
            </div>

            {/* Certificate Body Content */}
            <div className="relative z-10 text-center space-y-2 sm:space-y-3 pt-1 sm:pt-2">
              {/* Title */}
              <div>
                <h2 className="text-xl sm:text-3xl font-serif font-black text-[#0b1e3d] tracking-wider">
                  CERTIFICATE OF COMPLETION
                </h2>
                <div className="flex items-center justify-center gap-2 mt-1">
                  <div className="w-16 sm:w-28 h-[1px] bg-[#d4af37]" />
                  <div className="w-1.5 h-1.5 rotate-45 bg-[#d4af37]" />
                  <div className="w-16 sm:w-28 h-[1px] bg-[#d4af37]" />
                </div>
              </div>

              {/* Statement 1 */}
              <p className="text-[10px] sm:text-xs font-bold text-slate-500 uppercase tracking-widest pt-1">
                THIS IS TO CERTIFY THAT
              </p>

              {/* Student Name */}
              <div className="py-0.5">
                <h3 className="text-lg sm:text-2xl font-serif font-bold text-[#0b1e3d] underline decoration-[#d4af37] decoration-1 underline-offset-4 tracking-wide">
                  {displayName}
                </h3>
              </div>

              {/* Completion Description */}
              <div className="space-y-0.5 text-xs sm:text-sm text-slate-700 font-serif italic max-w-xl mx-auto">
                <p>has successfully completed the prescribed learning modules and passed the final assessment</p>
                <p className="text-[10px] sm:text-xs font-sans font-bold text-slate-500 uppercase tracking-wider not-italic pt-1">
                  FOR THE COURSE
                </p>
              </div>

              {/* Course Title */}
              <div>
                <h4 className="text-base sm:text-xl font-serif font-black text-[#0b1e3d] tracking-normal">
                  {certificate.course_title.toUpperCase()}
                </h4>
              </div>

              {/* Metadata Table (4 Columns: Skill, Score, Certificate ID, Issue Date) */}
              <div className="pt-2 sm:pt-3 max-w-2xl mx-auto">
                <div className="grid grid-cols-4 bg-white rounded-lg border border-slate-300 shadow-xs overflow-hidden text-[10px] sm:text-xs">
                  <div className="border-r border-slate-200">
                    <div className="bg-slate-100 font-bold text-[#0b1e3d] py-1 border-b border-slate-200 text-[9px] sm:text-[10px] uppercase">
                      Skill
                    </div>
                    <div className="p-1.5 font-bold text-slate-800 truncate">
                      {displaySkill}
                    </div>
                  </div>

                  <div className="border-r border-slate-200">
                    <div className="bg-slate-100 font-bold text-[#0b1e3d] py-1 border-b border-slate-200 text-[9px] sm:text-[10px] uppercase">
                      Assessment Score
                    </div>
                    <div className="p-1.5 font-bold text-slate-800">
                      {displayScore}
                    </div>
                  </div>

                  <div className="border-r border-slate-200">
                    <div className="bg-slate-100 font-bold text-[#0b1e3d] py-1 border-b border-slate-200 text-[9px] sm:text-[10px] uppercase">
                      Certificate ID
                    </div>
                    <div className="p-1.5 font-mono font-bold text-[#0b1e3d] truncate">
                      {certNumber}
                    </div>
                  </div>

                  <div>
                    <div className="bg-slate-100 font-bold text-[#0b1e3d] py-1 border-b border-slate-200 text-[9px] sm:text-[10px] uppercase">
                      Issue Date
                    </div>
                    <div className="p-1.5 font-bold text-slate-800 truncate">
                      {issueDateFormatted}
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Signatures & QR Code */}
              <div className="pt-3 sm:pt-6 grid grid-cols-3 items-end max-w-2xl mx-auto">
                {/* Signatory 1 */}
                <div className="text-center">
                  <div className="w-28 sm:w-36 h-[1px] bg-slate-400 mx-auto mb-1" />
                  <p className="text-[10px] sm:text-xs font-bold text-[#0b1e3d]">{sig1Title}</p>
                  <p className="text-[8px] sm:text-[9px] text-slate-500">{sig1Name}</p>
                </div>

                {/* Center QR Code */}
                <div className="flex flex-col items-center justify-center">
                  <div className="p-1 bg-white border border-slate-300 rounded shadow-xs">
                    <img
                      src={`/api/certificates/${certId}/qr/`}
                      alt="Verification QR"
                      className="w-14 h-14 sm:w-16 sm:h-16 object-contain"
                      onError={(e) => {
                        // In case endpoint is unreachable during unit test preview, show fallback box
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  </div>
                  <span className="text-[8px] font-bold text-[#0b1e3d] tracking-wider mt-1 uppercase">
                    SCAN TO VERIFY
                  </span>
                </div>

                {/* Signatory 2 */}
                <div className="text-center">
                  <div className="w-28 sm:w-36 h-[1px] bg-slate-400 mx-auto mb-1" />
                  <p className="text-[10px] sm:text-xs font-bold text-[#0b1e3d]">{sig2Title}</p>
                  <p className="text-[8px] sm:text-[9px] text-slate-500">{sig2Name}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Action Footer */}
        <div className="bg-white px-6 py-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200">
          <div className="text-xs text-slate-500">
            Certificate Number: <strong className="text-slate-900 font-mono">{certNumber}</strong>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={`/api/certificates/${certId}/pdf/`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-[#0b1e3d] hover:bg-[#142d57] text-white text-xs font-bold rounded-xl shadow transition flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[#d4af37]" />
              <span>Download Official PDF</span>
            </a>

            <a
              href={`/verify/${certNumber}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl border border-slate-300 transition flex items-center gap-1.5 cursor-pointer"
            >
              <ExternalLink className="w-3.5 h-3.5 text-primary-900" />
              <span>Public Verification</span>
            </a>

            <button
              onClick={onClose}
              className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl border border-slate-300 transition"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
