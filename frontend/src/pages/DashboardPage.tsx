import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import type { Enrollment, Certificate } from '../types';
import { 
  BookOpen, 
  ArrowRight, 
  Compass, 
  GraduationCap, 
  Award, 
  Download, 
  ExternalLink, 
  Eye, 
  ShieldCheck, 
  ShieldAlert 
} from 'lucide-react';
import { CertificatePreviewModal } from '../components/CertificatePreviewModal';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);

  // Certificate Preview Modal State
  const [selectedCert, setSelectedCert] = useState<Certificate | null>(null);
  const [isCertModalOpen, setIsCertModalOpen] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [enrRes, certRes] = await Promise.allSettled([
        apiClient.get('/learning/enrollments/'),
        apiClient.get('/certificates/my/')
      ]);

      if (enrRes.status === 'fulfilled') {
        setEnrollments(enrRes.value.data.results || enrRes.value.data);
      }
      if (certRes.status === 'fulfilled') {
        setCertificates(certRes.value.data);
      }
    } catch {
      // Handled gracefully
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenCertificate = (cert: Certificate) => {
    setSelectedCert(cert);
    setIsCertModalOpen(true);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 min-h-[80vh]">
      {/* Student Profile Header */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary-900 text-accent-500 font-extrabold text-2xl flex items-center justify-center">
            {user?.first_name ? user.first_name[0] : 'S'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">
                Welcome, {user?.first_name || user?.username}
              </h1>
              {user?.is_demo && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                  DEMO ACCOUNT
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Roll No: {user?.register_number || 'FXEC-STUDENT'} • {user?.department_details?.name || 'Francis Xavier Engineering College'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/catalogue"
            className="px-5 py-2.5 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-semibold text-xs shadow-sm flex items-center gap-2 transition-colors"
          >
            <BookOpen className="w-4 h-4 text-accent-400" />
            Browse New Courses
          </Link>
        </div>
      </div>

      {/* Student Learning Focus Banner */}
      <div className="bg-gradient-to-r from-primary-950 via-primary-900 to-slate-900 rounded-3xl p-6 sm:p-8 mb-8 text-white flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl border border-primary-800/80 relative overflow-hidden">
        <div className="space-y-2 max-w-2xl relative z-10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent-500/20 text-accent-300 text-xs font-bold border border-accent-500/30">
            <GraduationCap className="w-4 h-4 text-accent-400" />
            Francis Xavier Institutional Learning Hub
          </div>
          <h2 className="text-xl sm:text-2xl font-black tracking-tight">
            Accelerate Your Engineering Competencies
          </h2>
          <p className="text-xs text-slate-300 leading-relaxed">
            Follow approved department curricula, master core engineering topics through structured revision notes and practice challenges, and take proctored assessments to earn verified digital credentials.
          </p>
        </div>
        <Link
          to="/catalogue"
          className="px-6 py-3 bg-gradient-to-r from-accent-500 to-amber-400 hover:from-accent-400 hover:to-amber-300 text-slate-950 font-extrabold text-xs rounded-xl shadow-xl transition-all flex items-center gap-2 self-start md:self-auto shrink-0 relative z-10"
        >
          <Compass className="w-4 h-4 text-slate-950" />
          Explore Skill Catalogue
        </Link>
        <div className="absolute right-0 top-0 -mt-10 -mr-10 w-80 h-80 bg-accent-500/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* =================================================================== */}
      {/* MY CERTIFICATES SECTION (OFFICIAL MASTER PROMPT REQUIREMENT #33)     */}
      {/* =================================================================== */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-primary-900" />
            <h2 className="text-lg font-bold text-slate-900">
              My Certificates
            </h2>
            <span className="ml-1 px-2 py-0.5 rounded-full text-xs font-bold bg-primary-100 text-primary-900">
              {certificates.length}
            </span>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            Official verifiable credentials issued by Francis Xavier Engineering College
          </p>
        </div>

        {certificates.length === 0 ? (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-3 shadow-xs">
            <Award className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="font-bold text-slate-800 text-sm">No Certificates Issued Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
              Complete all required course learning modules and pass the final evaluation assessment to claim your official accredited institutional certificate.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px] font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3.5">Course Title</th>
                    <th className="px-6 py-3.5">Skill Track</th>
                    <th className="px-6 py-3.5">Assessment Score</th>
                    <th className="px-6 py-3.5">Certificate ID</th>
                    <th className="px-6 py-3.5">Issue Date</th>
                    <th className="px-6 py-3.5">Status</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {certificates.map((cert) => {
                    const isRevoked = cert.is_revoked || cert.status === 'REVOKED';
                    return (
                      <tr key={cert.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-6 py-4 font-bold text-slate-900">
                          {cert.course_title}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-800 font-semibold text-[11px]">
                            {cert.skill || 'Specialization'}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-bold text-primary-900">
                          {cert.score || cert.assessment_score || 'Passed'}
                        </td>
                        <td className="px-6 py-4 font-mono text-[11px] font-bold text-slate-800">
                          {cert.certificate_number}
                        </td>
                        <td className="px-6 py-4 text-slate-600">
                          {cert.issue_date || (cert.issued_at ? new Date(cert.issued_at).toLocaleDateString() : 'Issued')}
                        </td>
                        <td className="px-6 py-4">
                          {isRevoked ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">
                              <ShieldAlert className="w-3 h-3" /> Revoked
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              <ShieldCheck className="w-3 h-3" /> Valid
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {/* Action 1: View Certificate */}
                            <button
                              type="button"
                              onClick={() => handleOpenCertificate(cert)}
                              className="px-3 py-1.5 rounded-lg bg-primary-50 text-primary-900 hover:bg-primary-100 font-bold text-[11px] flex items-center gap-1 transition-colors cursor-pointer"
                              title="Preview Certificate"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>View</span>
                            </button>

                            {/* Action 2: Download PDF */}
                            <a
                              href={`/api/certificates/${cert.id}/pdf/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1.5 rounded-lg bg-[#0b1e3d] text-white hover:bg-[#152e59] font-bold text-[11px] flex items-center gap-1 shadow-xs transition-colors cursor-pointer"
                              title="Download Landscape PDF"
                            >
                              <Download className="w-3.5 h-3.5 text-[#d4af37]" />
                              <span>PDF</span>
                            </a>

                            {/* Action 3: Verify */}
                            <a
                              href={`/verify/${cert.certificate_number}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 font-semibold text-[11px] flex items-center gap-1 transition-colors cursor-pointer"
                              title="Public QR Verification"
                            >
                              <ExternalLink className="w-3 h-3 text-slate-500" />
                              <span>Verify</span>
                            </a>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Active Learning Section */}
      <div className="mb-8">
        <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-primary-900" />
          Enrolled Skill Tracks
        </h2>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading progress...</div>
        ) : enrollments.length === 0 ? (
          <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-3">
            <BookOpen className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="font-bold text-slate-800 text-sm">No Active Enrollments</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              You have not enrolled in any skill modules yet. Explore the catalogue to begin your personalized learning journey.
            </p>
            <Link
              to="/catalogue"
              className="inline-flex items-center gap-1 text-xs font-bold text-primary-900 hover:underline pt-2"
            >
              Go to Catalogue <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {enrollments.map((enr) => (
              <div key={enr.id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-primary-100 text-primary-900">
                      {enr.course.department?.code || 'INSTITUTIONAL'}
                    </span>
                    <h3 className="font-bold text-slate-900 text-base mt-1.5">{enr.course.title}</h3>
                  </div>
                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${
                    enr.is_completed 
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' 
                      : 'bg-amber-100 text-amber-800 border border-amber-200'
                  }`}>
                    {enr.is_completed ? '✓ Completed' : 'In Progress'}
                  </span>
                </div>

                <div className="flex justify-between items-center pt-2 text-xs border-t border-slate-100">
                  <span className="text-slate-500">
                    Course Modules
                  </span>
                  <Link
                    to={`/learn/${enr.course.slug}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-primary-900 hover:bg-primary-800 text-white font-bold rounded-lg transition-colors shadow-xs"
                  >
                    Open Course Modules <ArrowRight className="w-3.5 h-3.5 text-accent-400" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Certificate Preview Modal */}
      <CertificatePreviewModal
        certificate={selectedCert}
        isOpen={isCertModalOpen}
        onClose={() => setIsCertModalOpen(false)}
        studentNameFallback={user?.first_name ? `${user.first_name} ${user.last_name || ''}` : user?.username}
      />
    </div>
  );
};
