import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Certificate } from '../types';
import { 
  ShieldCheck, 
  ShieldAlert, 
  AlertCircle, 
  Download, 
  Award, 
  Calendar, 
  Hash, 
  ExternalLink,
  BookOpen,
  CheckCircle2,
  Eye,
  Check
} from 'lucide-react';
import { CertificatePreviewModal } from '../components/CertificatePreviewModal';

export const CertificateVerify: React.FC = () => {
  const { certificateId } = useParams<{ certificateId: string }>();
  const [certData, setCertData] = useState<Certificate | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<'REVOKED' | 'NOT_FOUND' | 'SERVER_ERROR' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  useEffect(() => {
    const verifyCert = async () => {
      if (!certificateId) return;
      try {
        setLoading(true);
        const res = await apiClient.get(`/certificates/verify/${certificateId}/`);
        if (res.data.status === 'VALID') {
          setCertData({
            ...res.data,
            id: certificateId
          });
        } else if (res.data.status === 'REVOKED') {
          setErrorStatus('REVOKED');
          setCertData({
            ...res.data,
            id: certificateId
          });
        } else {
          setErrorStatus('NOT_FOUND');
          setErrorMessage(res.data.message || 'CERTIFICATE NOT FOUND: No certificate record found for this identifier.');
        }
      } catch (err: any) {
        if (err.response?.status === 404) {
          setErrorStatus('NOT_FOUND');
          setErrorMessage('CERTIFICATE NOT FOUND: Certificate identifier does not exist in the institutional registry.');
        } else {
          setErrorStatus('SERVER_ERROR');
          setErrorMessage('An error occurred while contacting the institutional verification authority.');
        }
      } finally {
        setLoading(false);
      }
    };

    verifyCert();
  }, [certificateId]);

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Validating cryptographic signature with FXEC Registry...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
      {/* Verification Status Banner */}
      {certData && !errorStatus ? (
        <div className="bg-white rounded-2xl border-2 border-emerald-500/40 shadow-xl overflow-hidden">
          {/* Top Status Header */}
          <div className="bg-emerald-600 text-white px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="w-6 h-6 text-white" />
              <div>
                <h2 className="text-base font-bold flex items-center gap-2">
                  <Check className="w-5 h-5 text-emerald-200" /> VALID CERTIFICATE
                </h2>
                <p className="text-[11px] text-emerald-100">
                  Cryptographically verified against the Francis Xavier Engineering College record ledger
                </p>
              </div>
            </div>
            <span className="bg-white text-emerald-800 text-xs font-black px-3.5 py-1 rounded-full uppercase tracking-wider shadow-sm">
              Status: VALID
            </span>
          </div>

          <div className="p-6 sm:p-8 space-y-6">
            {/* Institution Badge */}
            <div className="flex items-start justify-between border-b border-slate-100 pb-6">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  Institution
                </span>
                <h3 className="text-lg font-extrabold text-[#0b1e3d] mt-0.5">
                  {certData.institution || 'Francis Xavier Engineering College'}
                </h3>
                <p className="text-xs text-slate-500">
                  Autonomous Institution • Tirunelveli, Tamil Nadu, India
                </p>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-bold">
                    Anna University Affiliated
                  </span>
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-bold">
                    NAAC 'A' Grade
                  </span>
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-bold">
                    NBA Accredited
                  </span>
                </div>
              </div>

              <img 
                src="/fxec_crest.png" 
                alt="FXEC Institutional Crest" 
                className="w-16 h-16 object-contain rounded-full shadow-md bg-white p-0.5 border border-slate-200" 
              />
            </div>

            {/* Credential Data Fields (Section 14 fields) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5 text-primary-800" /> Student Name
                </span>
                <p className="text-base font-bold text-slate-900">{certData.student_name}</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-primary-800" /> Course
                </span>
                <p className="text-base font-bold text-slate-900">{certData.course_title}</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-primary-800" /> Skill
                </span>
                <p className="text-sm font-bold text-slate-800">{certData.skill || 'Specialization Track'}</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-primary-800" /> Certificate ID
                </span>
                <p className="font-mono text-sm font-bold text-primary-950">{certData.certificate_number}</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-primary-800" /> Issue Date
                </span>
                <p className="text-xs font-semibold text-slate-800">
                  {certData.issue_date || (certData.issued_at ? new Date(certData.issued_at).toLocaleDateString('en-US', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                  }).toUpperCase() : 'Verified')}
                </p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Assessment Status
                </span>
                <p className="text-xs font-bold text-emerald-700 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  {certData.assessment_status || 'PASSED'} ({certData.score || '85 / 100'})
                </p>
              </div>
            </div>

            {/* Cryptographic Hash Section */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-600 flex items-center gap-1">
                  <Hash className="w-3.5 h-3.5 text-slate-400" /> SHA-256 Tamper-Proof Signature
                </span>
                <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold">
                  Matched Database Record
                </span>
              </div>
              <p className="font-mono text-[11px] text-slate-700 break-all bg-white p-2.5 rounded-lg border border-slate-200">
                {certData.integrity_hash}
              </p>
              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                <span>Canonical ID: <strong className="text-slate-900">{certData.certificate_number}</strong></span>
                {certData.is_demo && (
                  <span className="text-amber-700 bg-amber-100 px-2 py-0.5 rounded text-[10px] font-bold">
                    Demo Verification Environment
                  </span>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsPreviewOpen(true)}
                  className="px-4 py-2.5 bg-primary-50 hover:bg-primary-100 text-primary-950 rounded-xl text-xs font-bold border border-primary-200 transition-all flex items-center gap-2 cursor-pointer"
                >
                  <Eye className="w-4 h-4 text-primary-900" /> View Certificate
                </button>

                <a
                  href={`/api/certificates/${certData.certificate_number || certificateId}/pdf/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-5 py-2.5 bg-[#0b1e3d] hover:bg-[#152e59] text-white rounded-xl text-xs font-bold shadow transition-all flex items-center gap-2 cursor-pointer"
                >
                  <Download className="w-4 h-4 text-[#d4af37]" /> Download Official PDF Certificate
                </a>
              </div>

              <a
                href="https://francisxavier.ac.in"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-slate-500 hover:text-primary-900 font-semibold flex items-center gap-1"
              >
                francisxavier.ac.in <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>
      ) : errorStatus === 'REVOKED' ? (
        <div className="bg-white rounded-2xl border-2 border-red-500/40 shadow-xl overflow-hidden p-8 space-y-6">
          <div className="flex items-center gap-3 text-red-600">
            <ShieldAlert className="w-9 h-9" />
            <div>
              <h2 className="text-xl font-bold tracking-tight">CERTIFICATE REVOKED</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                This academic credential has been officially invalidated by the institutional council.
              </p>
            </div>
          </div>
          <div className="p-4 rounded-xl bg-red-50 text-red-900 text-xs space-y-1.5 border border-red-200">
            <p><strong>Certificate ID:</strong> {certData?.certificate_number || certificateId}</p>
            <p><strong>Student:</strong> {certData?.student_name || 'Recorded Candidate'}</p>
            <p><strong>Course:</strong> {certData?.course_title || 'Enrolled Subject'}</p>
            <p><strong>Revocation Reason:</strong> {certData?.revocation_reason || 'Administrative or academic policy revocation'}</p>
            <p><strong>Revocation Timestamp:</strong> {certData?.revoked_at ? new Date(certData.revoked_at).toLocaleString() : 'Recorded'}</p>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xl p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center mx-auto">
            <AlertCircle className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">CERTIFICATE NOT FOUND</h2>
          <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
            {errorMessage || 'The requested certificate identifier does not match any authentic credential issued in the Francis Xavier Engineering College record ledger.'}
          </p>
          <div className="pt-4">
            <Link
              to="/catalogue"
              className="px-5 py-2.5 bg-primary-900 text-white rounded-xl text-xs font-semibold inline-block hover:bg-primary-800 transition"
            >
              Explore Official Courses
            </Link>
          </div>
        </div>
      )}

      {/* Institutional Provenance Footer */}
      <div className="text-center text-xs text-slate-400 space-y-1">
        <p>Francis Xavier Engineering College (Autonomous), Vannarpettai, Tirunelveli — 627003</p>
        <p>Accredited by NBA &amp; NAAC 'A' Grade • Approved by AICTE, New Delhi</p>
      </div>

      {/* Certificate Preview Modal */}
      {certData && (
        <CertificatePreviewModal
          certificate={certData}
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          studentNameFallback={certData.student_name}
        />
      )}
    </div>
  );
};
