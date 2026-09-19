import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import type { Course, AISkillSuggestion, FacultyMember, Department, User } from '../types';
import { 
  Mail, 
  ExternalLink, 
  RefreshCw,
  Activity,
  CheckCircle2,
  XCircle,
  Sparkles,
  ShieldCheck,
  BookOpen,
  Flag,
  Award,
  Sliders,
  Search,
  RotateCcw,
  ShieldAlert,
  Upload,
  Download,
  Eye,
  Check,
  Trash2,
  Users,
  GraduationCap,
  UserPlus,
  Edit2,
  UserCheck,
  UserX,
  Phone,
  Building,
  Building2,
  Plus,
  Key,
  Clock,
  Send
} from 'lucide-react';

import { AICourseGeneratorModal } from '../components/AICourseGeneratorModal';
import { CertificatePreviewModal } from '../components/CertificatePreviewModal';

interface ProvenanceCourse {
  id: number;
  title: string;
  department: string;
  source_type: string;
  source_url: string;
  source_title: string;
  source_accessed_at: string;
  last_verified_at: string;
  content_status: string;
  is_demo: boolean;
}

interface AuditLogItem {
  id: number;
  user: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address?: string;
  metadata: any;
  timestamp: string;
}

interface EmailLogItem {
  id: string | number;
  recipient_email: string;
  subject: string;
  certificate_number?: string;
  status: string;
  sent_at?: string;
  error_message?: string;
  created_at: string;
}

export const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'faculty' | 'students' | 'departments' | 'proposals' | 'all_courses' | 'ai_suggestions' | 'reported_videos' | 'provenance' | 'audit' | 'email' | 'certificates' | 'branding'>('faculty');
  const [loading, setLoading] = useState(true);
  const [isGeneratorOpen, setIsGeneratorOpen] = useState(false);
  const [generatorSkillName, setGeneratorSkillName] = useState('');

  // Overview Stats
  const [overviewStats, setOverviewStats] = useState<{
    total_faculty: number;
    active_faculty: number;
    total_students: number;
    total_courses: number;
    pending_courses: number;
    total_departments: number;
  } | null>(null);

  // Departments List (Active)
  const [departments, setDepartments] = useState<Department[]>([]);

  // Department Master Management State (All Departments)
  const [adminDepartments, setAdminDepartments] = useState<Department[]>([]);
  const [deptSearch, setDeptSearch] = useState('');
  const [deptStatusFilter, setDeptStatusFilter] = useState('');
  const [isAddDeptModalOpen, setIsAddDeptModalOpen] = useState(false);
  const [addDeptLoading, setAddDeptLoading] = useState(false);
  const [addDeptError, setAddDeptError] = useState<string | null>(null);
  const [addDeptForm, setAddDeptForm] = useState({
    code: '',
    name: '',
    description: '',
    is_active: true
  });

  // Faculty Management State
  const [facultyList, setFacultyList] = useState<FacultyMember[]>([]);
  const [facultySearch, setFacultySearch] = useState('');
  const [facultyDeptFilter, setFacultyDeptFilter] = useState('');
  const [facultyStatusFilter, setFacultyStatusFilter] = useState('');
  const [isAddFacultyModalOpen, setIsAddFacultyModalOpen] = useState(false);
  const [addFacultyLoading, setAddFacultyLoading] = useState(false);
  const [addFacultyError, setAddFacultyError] = useState<string | null>(null);
  const [addFacultyForm, setAddFacultyForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    faculty_id: '',
    department: '',
    phone: '',
    password: '',
    is_active: true
  });

  const [editingFaculty, setEditingFaculty] = useState<FacultyMember | null>(null);
  const [editFacultyLoading, setEditFacultyLoading] = useState(false);
  const [editFacultyError, setEditFacultyError] = useState<string | null>(null);
  const [editFacultyForm, setEditFacultyForm] = useState({
    first_name: '',
    last_name: '',
    faculty_id: '',
    department: '',
    phone: '',
    password: '',
    is_active: true
  });

  // Student Directory State
  const [studentList, setStudentList] = useState<User[]>([]);
  const [studentSearch, setStudentSearch] = useState('');
  const [studentDeptFilter, setStudentDeptFilter] = useState('');
  const [studentYearFilter, setStudentYearFilter] = useState('');

  // Course Management State
  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [courseSearch, setCourseSearch] = useState('');

  // Certificate Management State
  const [adminCerts, setAdminCerts] = useState<any[]>([]);
  const [certSearch, setCertSearch] = useState('');
  const [certConfig, setCertConfig] = useState<any>(null);
  const [previewCert, setPreviewCert] = useState<any>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [uploadingAsset, setUploadingAsset] = useState<string | null>(null);
  const [configSaved, setConfigSaved] = useState(false);

  // Existing Audit Data
  const [provenanceList, setProvenanceList] = useState<ProvenanceCourse[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [emailLogs, setEmailLogs] = useState<EmailLogItem[]>([]);

  // Proposals & AI Suggestions Data
  const [pendingProposals, setPendingProposals] = useState<Course[]>([]);
  const [aiSuggestions, setAiSuggestions] = useState<AISkillSuggestion[]>([]);
  const [reportedVideos, setReportedVideos] = useState<any[]>([]);
  const [replacementUrls, setReplacementUrls] = useState<{ [id: number]: string }>({});
  const [actionInProgressId, setActionInProgressId] = useState<number | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      const res = await apiClient.get('/admin/overview/');
      setOverviewStats(res.data);
    } catch (e) {
      console.error('Failed to load overview stats', e);
    }
  };

  const fetchDepartments = async () => {
    try {
      const res = await apiClient.get('/catalogue/departments/');
      const depts = Array.isArray(res.data) ? res.data : (res.data.results || []);
      setDepartments(depts);
    } catch (e) {
      console.error('Failed to load active departments', e);
    }
  };

  const fetchAdminDepartments = async () => {
    try {
      const params = new URLSearchParams();
      if (deptSearch) params.append('search', deptSearch);
      if (deptStatusFilter) params.append('is_active', deptStatusFilter);
      const res = await apiClient.get(`/catalogue/admin/departments/?${params.toString()}`);
      const list = Array.isArray(res.data) ? res.data : (res.data.results || []);
      setAdminDepartments(list);
    } catch (e) {
      console.error('Failed to load admin departments', e);
      setAdminDepartments([]);
    }
  };

  const fetchFaculty = async () => {
    try {
      const params = new URLSearchParams();
      if (facultySearch) params.append('search', facultySearch);
      if (facultyDeptFilter) params.append('department', facultyDeptFilter);
      if (facultyStatusFilter) params.append('is_active', facultyStatusFilter);
      const res = await apiClient.get(`/admin/faculty/?${params.toString()}`);
      const data = res.data;
      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.faculty)
        ? data.faculty
        : Array.isArray(data?.results)
        ? data.results
        : [];
      setFacultyList(list);
    } catch (e) {
      console.error('Failed to load faculty', e);
      setFacultyList([]);
    }
  };

  const fetchStudents = async () => {
    try {
      const params = new URLSearchParams();
      if (studentSearch) params.append('search', studentSearch);
      if (studentDeptFilter) params.append('department', studentDeptFilter);
      if (studentYearFilter) params.append('year', studentYearFilter);
      const res = await apiClient.get(`/admin/students/?${params.toString()}`);
      const data = res.data;
      const list = Array.isArray(data)
        ? data
        : Array.isArray(data?.students)
        ? data.students
        : Array.isArray(data?.results)
        ? data.results
        : [];
      setStudentList(list);
    } catch (e) {
      console.error('Failed to load students', e);
      setStudentList([]);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      setActionMessage(null);
      fetchOverview();
      fetchDepartments();

      // Always populate counts for both faculty and students
      fetchFaculty();
      fetchStudents();

      if (activeTab === 'faculty') {
        await fetchFaculty();
      } else if (activeTab === 'students') {
        await fetchStudents();
      } else if (activeTab === 'departments') {
        await fetchAdminDepartments();
      } else if (activeTab === 'proposals') {
        const res = await apiClient.get('/catalogue/admin/course-proposals/');
        setPendingProposals(res.data.results || res.data);
      } else if (activeTab === 'all_courses') {
        const res = await apiClient.get('/catalogue/courses/?sort=newest');
        setAllCourses(res.data.results || res.data);
      } else if (activeTab === 'ai_suggestions') {
        const res = await apiClient.get('/catalogue/admin/ai-suggestions/');
        setAiSuggestions(res.data.results || res.data);
      } else if (activeTab === 'reported_videos') {
        const res = await apiClient.get('/catalogue/admin/reported-videos/?status=OPEN');
        setReportedVideos(res.data);
      } else if (activeTab === 'provenance') {
        const res = await apiClient.get('/audit/provenance/');
        setProvenanceList(res.data);
      } else if (activeTab === 'audit') {
        const res = await apiClient.get('/audit/logs/');
        setAuditLogs(res.data);
      } else if (activeTab === 'email') {
        const res = await apiClient.get('/notifications/logs/');
        setEmailLogs(res.data);
      } else if (activeTab === 'certificates') {
        const res = await apiClient.get(`/certificates/admin/?q=${encodeURIComponent(certSearch)}`);
        setAdminCerts(res.data);
      } else if (activeTab === 'branding') {
        const cfgRes = await apiClient.get('/certificates/admin/config/');
        setCertConfig(cfgRes.data);
      }
    } catch (err) {
      console.error('Failed to load admin data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'faculty') {
      const delay = setTimeout(fetchFaculty, 250);
      return () => clearTimeout(delay);
    }
  }, [facultySearch, facultyDeptFilter, facultyStatusFilter]);

  useEffect(() => {
    if (activeTab === 'students') {
      const delay = setTimeout(fetchStudents, 250);
      return () => clearTimeout(delay);
    }
  }, [studentSearch, studentDeptFilter, studentYearFilter]);

  useEffect(() => {
    if (activeTab === 'departments') {
      const delay = setTimeout(fetchAdminDepartments, 250);
      return () => clearTimeout(delay);
    }
  }, [deptSearch, deptStatusFilter]);

  // Toggle Department Active / Inactive Status
  const handleToggleDeptStatus = async (deptId: number, code: string) => {
    try {
      setActionInProgressId(deptId);
      const res = await apiClient.post(`/catalogue/admin/departments/${deptId}/toggle-status/`);
      setActionMessage(`Department '${code}' status set to: ${res.data.is_active ? 'ACTIVE' : 'INACTIVE'}.`);
      fetchAdminDepartments();
      fetchDepartments();
      fetchOverview();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to update department status');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Add Department Submit
  const handleAddDeptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddDeptError(null);
    const code = addDeptForm.code.trim().toUpperCase();
    const name = addDeptForm.name.trim();

    if (!code) {
      setAddDeptError('Department code is required (e.g. CSE, ECE).');
      return;
    }
    if (!name) {
      setAddDeptError('Department name is required.');
      return;
    }

    try {
      setAddDeptLoading(true);
      await apiClient.post('/catalogue/admin/departments/', {
        code,
        name,
        description: addDeptForm.description.trim(),
        is_active: addDeptForm.is_active
      });
      setIsAddDeptModalOpen(false);
      setAddDeptForm({ code: '', name: '', description: '', is_active: true });
      setActionMessage(`Department '${code} - ${name}' created successfully.`);
      fetchAdminDepartments();
      fetchDepartments();
      fetchOverview();
    } catch (err: any) {
      setAddDeptError(err?.response?.data?.error || 'Failed to create department.');
    } finally {
      setAddDeptLoading(false);
    }
  };

  // Toggle Faculty Active / Inactive Status
  const handleToggleFacultyStatus = async (facultyId: number, name: string) => {
    try {
      setActionInProgressId(facultyId);
      const res = await apiClient.post(`/admin/faculty/${facultyId}/toggle-status/`);
      setActionMessage(`Faculty member '${name}' status set to: ${res.data.is_active ? 'ACTIVE' : 'INACTIVE'}.`);
      fetchFaculty();
      fetchOverview();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to update faculty status');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Add Faculty Submit
  const handleAddFacultySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddFacultyError(null);

    const email = addFacultyForm.email.trim().toLowerCase();
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!email || !emailRegex.test(email)) {
      setAddFacultyError('Please enter a valid email address.');
      return;
    }

    if (!addFacultyForm.department) {
      setAddFacultyError('Please select a department for the faculty member.');
      return;
    }

    try {
      setAddFacultyLoading(true);
      const res = await apiClient.post('/admin/faculty/', {
        first_name: addFacultyForm.first_name,
        last_name: addFacultyForm.last_name,
        email,
        faculty_id: addFacultyForm.faculty_id,
        department: parseInt(addFacultyForm.department),
        phone: addFacultyForm.phone,
        is_active: addFacultyForm.is_active
      });
      setIsAddFacultyModalOpen(false);
      setAddFacultyForm({
        first_name: '',
        last_name: '',
        email: '',
        faculty_id: '',
        department: '',
        phone: '',
        password: '',
        is_active: true
      });
      if (res.data?.email_sent === false) {
        setActionMessage('Faculty account created, but the invitation email could not be sent.');
      } else {
        setActionMessage(res.data?.message || 'New Faculty account created and invitation email dispatched.');
      }
      fetchFaculty();
      fetchOverview();
    } catch (err: any) {
      const data = err?.response?.data;
      if (typeof data === 'string') {
        setAddFacultyError(data);
      } else if (data?.detail) {
        setAddFacultyError(data.detail);
      } else if (data?.email) {
        setAddFacultyError(Array.isArray(data.email) ? data.email[0] : data.email);
      } else if (data?.faculty_id) {
        setAddFacultyError(Array.isArray(data.faculty_id) ? data.faculty_id[0] : data.faculty_id);
      } else if (data?.error) {
        setAddFacultyError(data.error);
      } else {
        setAddFacultyError('Failed to create faculty member. Please verify required fields.');
      }
    } finally {
      setAddFacultyLoading(false);
    }
  };

  // Resend Faculty Invitation Email
  const handleResendInvitation = async (facultyId: number, _name: string, email: string) => {
    try {
      setActionInProgressId(facultyId);
      const res = await apiClient.post(`/admin/faculty/${facultyId}/resend-invitation/`);
      setActionMessage(res.data?.message || `Invitation email resent to ${email}.`);
      fetchFaculty();
    } catch (err: any) {
      alert(err?.response?.data?.error || `Failed to resend invitation email to ${email}.`);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Open Edit Faculty Modal
  const handleOpenEditFaculty = (f: FacultyMember) => {
    setEditingFaculty(f);
    setEditFacultyError(null);
    setEditFacultyForm({
      first_name: f.first_name || '',
      last_name: f.last_name || '',
      faculty_id: f.faculty_id || f.register_number || '',
      department: f.department ? String(f.department) : '',
      phone: f.phone || '',
      password: '',
      is_active: f.is_active
    });
  };

  // Edit Faculty Submit
  const handleEditFacultySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingFaculty) return;
    setEditFacultyError(null);

    if (!editFacultyForm.department) {
      setEditFacultyError('Please select a department for the faculty member.');
      return;
    }

    try {
      setEditFacultyLoading(true);
      const payload: any = {
        first_name: editFacultyForm.first_name,
        last_name: editFacultyForm.last_name,
        faculty_id: editFacultyForm.faculty_id,
        department: parseInt(editFacultyForm.department),
        phone: editFacultyForm.phone,
        is_active: editFacultyForm.is_active
      };
      if (editFacultyForm.password && editFacultyForm.password.trim().length >= 8) {
        payload.password = editFacultyForm.password.trim();
      }
      await apiClient.patch(`/admin/faculty/${editingFaculty.id}/`, payload);
      setEditingFaculty(null);
      setActionMessage(`Faculty profile for '${editingFaculty.first_name || editingFaculty.username}' updated.`);
      fetchFaculty();
      fetchOverview();
    } catch (err: any) {
      const data = err?.response?.data;
      if (typeof data === 'string') {
        setEditFacultyError(data);
      } else if (data?.detail) {
        setEditFacultyError(data.detail);
      } else if (data?.faculty_id) {
        setEditFacultyError(Array.isArray(data.faculty_id) ? data.faculty_id[0] : data.faculty_id);
      } else {
        setEditFacultyError('Failed to update faculty profile.');
      }
    } finally {
      setEditFacultyLoading(false);
    }
  };

  // Approve Course Proposal
  const handleApproveProposal = async (courseId: number, title: string) => {
    try {
      setActionInProgressId(courseId);
      await apiClient.post(`/catalogue/admin/course-proposals/${courseId}/approve/`, {
        notes: 'Officially reviewed and verified by Academic Administration.'
      });
      setActionMessage(`Course '${title}' officially approved and published to student catalogue.`);
      fetchData();
    } catch (err) {
      console.error('Approval failed', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Reject Course Proposal
  const handleRejectProposal = async (courseId: number, title: string) => {
    const reason = prompt(`Enter rejection reason or required revisions for '${title}':`);
    if (reason === null) return;

    try {
      setActionInProgressId(courseId);
      await apiClient.post(`/catalogue/admin/course-proposals/${courseId}/reject/`, {
        notes: reason || 'Proposal requires curriculum adjustment.'
      });
      setActionMessage(`Course proposal '${title}' marked as rejected.`);
      fetchData();
    } catch (err) {
      console.error('Rejection failed', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Permanently Delete Faculty Member
  const handleDeleteFaculty = async (facultyId: number, name: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete faculty member "${name}"? This action cannot be undone.`)) return;
    try {
      setActionInProgressId(facultyId);
      const res = await apiClient.delete(`/admin/faculty/${facultyId}/`);
      setActionMessage(res.data.message || `Faculty member "${name}" deleted.`);
      fetchFaculty();
      fetchOverview();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete faculty member');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Permanently Delete Student
  const handleDeleteStudent = async (studentId: number, name: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete student "${name}"? This action cannot be undone.`)) return;
    try {
      setActionInProgressId(studentId);
      const res = await apiClient.delete(`/admin/students/${studentId}/`);
      setActionMessage(res.data.message || `Student record "${name}" deleted.`);
      fetchStudents();
      fetchOverview();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete student record');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Delete Reported Video Issue
  const handleDeleteReportedVideo = async (issueId: number) => {
    if (!window.confirm('Are you sure you want to delete this reported video issue?')) return;
    try {
      setActionInProgressId(issueId);
      await apiClient.delete(`/catalogue/admin/reported-videos/${issueId}/`);
      setActionMessage('Reported video issue deleted.');
      fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete reported video issue');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Delete Audit Log
  const handleDeleteAuditLog = async (logId: number) => {
    if (!window.confirm(`Delete audit log record #${logId}?`)) return;
    try {
      await apiClient.delete(`/audit/logs/${logId}/`);
      setActionMessage(`Audit log #${logId} deleted.`);
      fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete audit log');
    }
  };

  // Clear All Audit Logs
  const handleClearAuditLogs = async () => {
    if (!window.confirm('Are you sure you want to delete and clear ALL audit logs?')) return;
    try {
      await apiClient.delete('/audit/logs/');
      setActionMessage('All audit logs cleared.');
      fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to clear audit logs');
    }
  };

  // Delete Email / Notification Log
  const handleDeleteEmailLog = async (logId: string | number) => {
    if (!window.confirm(`Delete notification log #${logId}?`)) return;
    try {
      await apiClient.delete(`/notifications/logs/${logId}/`);
      setActionMessage(`Notification log #${logId} deleted.`);
      fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete notification log');
    }
  };

  // Clear All Email / Notification Logs
  const handleClearEmailLogs = async () => {
    if (!window.confirm('Are you sure you want to delete and clear ALL notification logs?')) return;
    try {
      await apiClient.delete('/notifications/logs/');
      setActionMessage('All notification logs cleared.');
      fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to clear notification logs');
    }
  };

  // Permanently Delete Course (Admin Power)
  const handleDeleteCourse = async (courseId: number, title: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete course "${title}"? All associated modules, lessons, and resources will be removed.`)) return;
    try {
      setActionInProgressId(courseId);
      await apiClient.delete(`/catalogue/admin/courses/${courseId}/delete/`);
      setActionMessage(`Course "${title}" permanently deleted from catalogue.`);
      fetchData();
      fetchOverview();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete course');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Delete AI Suggestion
  const handleDeleteAiSuggestion = async (suggId: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete AI skill suggestion "${title}"?`)) return;
    try {
      setActionInProgressId(suggId);
      await apiClient.delete(`/catalogue/admin/ai-suggestions/${suggId}/`);
      setActionMessage(`AI Suggestion "${title}" deleted.`);
      fetchData();
    } catch (err: any) {
      alert(err?.response?.data?.error || 'Failed to delete AI suggestion');
    } finally {
      setActionInProgressId(null);
    }
  };

  // Approve AI Suggestion
  const handleApproveAiSuggestion = async (suggId: number, title: string) => {
    try {
      setActionInProgressId(suggId);
      await apiClient.post(`/catalogue/admin/ai-suggestions/${suggId}/approve/`);
      setActionMessage(`AI Suggestion '${title}' promoted into approved institutional skill catalogue!`);
      fetchData();
    } catch (err) {
      console.error('Approve AI suggestion failed', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Verify Source Provenance
  const handleVerifySource = async (courseId: number) => {
    try {
      setActionInProgressId(courseId);
      await apiClient.post('/catalogue/admin/verify-source/', {
        resource_type: 'course',
        resource_id: courseId
      });
      fetchData();
    } catch (err) {
      console.error('Verify source failed', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Resolve Reported Video Issue
  const handleResolveIssue = async (issueId: number, action: 'RESOLVE' | 'DISMISS') => {
    try {
      setActionInProgressId(issueId);
      await apiClient.post(`/catalogue/admin/reported-videos/${issueId}/resolve/`, {
        action,
        replacement_youtube_url: replacementUrls[issueId] || ''
      });
      setActionMessage(`Reported video issue ${action.toLowerCase()}d successfully.`);
      fetchData();
    } catch (err) {
      console.error('Resolve issue failed', err);
    } finally {
      setActionInProgressId(null);
    }
  };

  // Admin Certificate Handlers
  const handleRevokeCert = async (certId: string, certNumber: string) => {
    const reason = window.prompt(`Enter institutional revocation reason for certificate ${certNumber}:`, 'Academic policy non-compliance');
    if (!reason) return;
    try {
      await apiClient.post(`/certificates/admin/${certId}/revoke/`, { reason });
      setActionMessage(`Certificate ${certNumber} has been revoked.`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to revoke certificate');
    }
  };

  const handleRestoreCert = async (certId: string, certNumber: string) => {
    if (!window.confirm(`Restore certificate ${certNumber} to VALID status?`)) return;
    try {
      await apiClient.post(`/certificates/admin/${certId}/restore/`);
      setActionMessage(`Certificate ${certNumber} restored to VALID.`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to restore certificate');
    }
  };

  const handleRegenerateCert = async (certId: string, certNumber: string) => {
    try {
      await apiClient.post(`/certificates/admin/${certId}/regenerate/`);
      setActionMessage(`Certificate ${certNumber} regenerated successfully.`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to regenerate certificate');
    }
  };

  const handleFileUpload = async (assetType: string, file: File) => {
    const formData = new FormData();
    formData.append('asset_type', assetType);
    formData.append('image', file);

    try {
      setUploadingAsset(assetType);
      await apiClient.post('/certificates/admin/branding/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setActionMessage(`Approved ${assetType} updated and set to active version.`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to upload branding asset');
    } finally {
      setUploadingAsset(null);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post('/certificates/admin/config/', certConfig);
      setConfigSaved(true);
      setTimeout(() => setConfigSaved(false), 3000);
      setActionMessage('Institutional certificate configuration updated.');
    } catch (err: any) {
      alert('Failed to update certificate configuration');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 min-h-[85vh] space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-primary-950 via-primary-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-purple-300 bg-purple-900/40 border border-purple-500/30 px-3 py-1 rounded-full">
            Autonomous Academic Administration
          </span>
          <h1 className="text-2xl sm:text-3xl font-black mt-2">
            Institutional Governance &amp; Proposal Review Console
          </h1>
          <p className="text-xs text-slate-300 mt-0.5">
            Admin: <strong className="text-white">{user?.username}</strong> • Francis Xavier Engineering College (Autonomous), Tirunelveli
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <button
            onClick={() => setIsGeneratorOpen(true)}
            className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md shadow-indigo-500/20 transition-all cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generate AI Course
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Console
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold rounded-2xl flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Overview Stats Cards */}
      {overviewStats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider">Faculty</span>
              <Users className="w-4 h-4 text-primary-900" />
            </div>
            <div className="text-xl font-black text-slate-900">{overviewStats.total_faculty}</div>
            <div className="text-[10px] text-emerald-600 font-semibold">{overviewStats.active_faculty} Active</div>
          </div>

          <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider">Students</span>
              <GraduationCap className="w-4 h-4 text-accent-600" />
            </div>
            <div className="text-xl font-black text-slate-900">{overviewStats.total_students}</div>
            <div className="text-[10px] text-slate-500 font-medium">Verified Enrolled</div>
          </div>

          <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider">Courses</span>
              <BookOpen className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-xl font-black text-slate-900">{overviewStats.total_courses}</div>
            <div className="text-[10px] text-emerald-600 font-semibold">Published</div>
          </div>

          <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider">Proposals</span>
              <Clock className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-xl font-black text-amber-600">{overviewStats.pending_courses}</div>
            <div className="text-[10px] text-amber-700 font-semibold">Pending Review</div>
          </div>

          <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider">Departments</span>
              <Building className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="text-xl font-black text-slate-900">{overviewStats.total_departments}</div>
            <div className="text-[10px] text-slate-500 font-medium">FXEC Programs</div>
          </div>

          <div className="p-4 bg-white border border-slate-200/80 rounded-2xl shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wider">Video Flags</span>
              <Flag className="w-4 h-4 text-rose-500" />
            </div>
            <div className="text-xl font-black text-rose-600">{reportedVideos.length}</div>
            <div className="text-[10px] text-slate-500 font-medium">Open Reports</div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 text-xs font-bold gap-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('faculty')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'faculty'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users className="w-4 h-4 text-primary-900" />
          Faculty Management ({facultyList.length || overviewStats?.total_faculty || 0})
        </button>

        <button
          onClick={() => setActiveTab('students')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'students'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <GraduationCap className="w-4 h-4 text-accent-600" />
          Student Directory ({studentList.length || overviewStats?.total_students || 0})
        </button>

        <button
          onClick={() => setActiveTab('departments')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'departments'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Building2 className="w-4 h-4 text-indigo-600" />
          Departments ({adminDepartments.length || departments.length || overviewStats?.total_departments || 0})
        </button>

        <button
          onClick={() => setActiveTab('proposals')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'proposals'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Course Proposals ({pendingProposals.length})
        </button>

        <button
          onClick={() => setActiveTab('all_courses')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'all_courses'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <BookOpen className="w-4 h-4 text-emerald-600" />
          All Courses Catalogue
        </button>

        <button
          onClick={() => setActiveTab('ai_suggestions')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'ai_suggestions'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sparkles className="w-4 h-4 text-accent-600" />
          AI Skill Suggestions ({aiSuggestions.length})
        </button>

        <button
          onClick={() => setActiveTab('reported_videos')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'reported_videos'
              ? 'border-rose-600 text-rose-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Flag className="w-4 h-4 text-rose-500" />
          Reported Videos Queue ({reportedVideos.length})
        </button>

        <button
          onClick={() => setActiveTab('provenance')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'provenance'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Source Provenance Ledger
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'audit'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Activity className="w-4 h-4 text-purple-600" />
          Security Audit Logs
        </button>

        <button
          onClick={() => setActiveTab('email')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'email'
              ? 'border-primary-900 text-primary-900'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Mail className="w-4 h-4 text-blue-600" />
          Notification Ledger
        </button>

        <button
          onClick={() => setActiveTab('certificates')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'certificates'
              ? 'border-amber-600 text-amber-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Award className="w-4 h-4 text-amber-600" />
          Certificates Registry
        </button>

        <button
          onClick={() => setActiveTab('branding')}
          className={`pb-3 px-4 flex items-center gap-2 transition-all border-b-2 ${
            activeTab === 'branding'
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4 text-indigo-600" />
          Branding &amp; Certificate Config
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB: FACULTY MANAGEMENT */}
      {/* ========================================================= */}
      {activeTab === 'faculty' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Users className="w-5 h-5 text-primary-900" />
                Faculty Management
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Administer institutional faculty credentials, department allocations, and teaching access.
              </p>
            </div>

            <button
              onClick={() => {
                setAddFacultyError(null);
                setIsAddFacultyModalOpen(true);
              }}
              className="px-4 py-2.5 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all cursor-pointer self-start sm:self-auto"
            >
              <UserPlus className="w-4 h-4" />
              Add Faculty Member
            </button>
          </div>

          {/* Search & Filter Controls */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row items-stretch md:items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={facultySearch}
                onChange={(e) => setFacultySearch(e.target.value)}
                placeholder="Search faculty by name, email, or faculty ID..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
              />
              {facultySearch && (
                <button
                  onClick={() => setFacultySearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={facultyDeptFilter}
                onChange={(e) => setFacultyDeptFilter(e.target.value)}
                className="px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
              >
                <option value="">All Departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.code}>
                    {d.code} - {d.name}
                  </option>
                ))}
              </select>

              <select
                value={facultyStatusFilter}
                onChange={(e) => setFacultyStatusFilter(e.target.value)}
                className="px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
              >
                <option value="">All Statuses</option>
                <option value="true">Active Only</option>
                <option value="false">Inactive Only</option>
              </select>
            </div>
          </div>

          {/* Faculty Table */}
          {loading ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : facultyList.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500 space-y-3">
              <Users className="w-10 h-10 text-slate-300 mx-auto" />
              <p className="font-semibold">No faculty members found matching your filter criteria.</p>
              <button
                onClick={() => {
                  setFacultySearch('');
                  setFacultyDeptFilter('');
                  setFacultyStatusFilter('');
                }}
                className="text-primary-900 underline text-xs font-bold"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Faculty Member</th>
                      <th className="py-3 px-4">Official Faculty Email</th>
                      <th className="py-3 px-4">Faculty ID</th>
                      <th className="py-3 px-4">Department</th>
                      <th className="py-3 px-4">Phone</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {facultyList.map((f) => {
                      const fullName = [f.first_name, f.last_name].filter(Boolean).join(' ') || f.username;
                      const initials = (fullName || 'F').slice(0, 2).toUpperCase();

                      return (
                        <tr key={f.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-primary-900/10 text-primary-900 flex items-center justify-center font-bold text-xs">
                                {initials}
                              </div>
                              <div>
                                <div className="font-bold text-slate-900">{fullName}</div>
                                <div className="text-[11px] text-slate-400 font-mono">@{f.username}</div>
                              </div>
                            </div>
                          </td>

                          <td className="py-3 px-4">
                            <div className="flex items-center gap-1.5 font-mono text-slate-600">
                              <span>{f.email}</span>
                              <span title="Official Faculty Account">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                              </span>
                            </div>
                          </td>

                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[11px] font-semibold">
                              {f.faculty_id || f.register_number || '—'}
                            </span>
                          </td>

                          <td className="py-3 px-4">
                            <span className="px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 font-semibold text-[11px]">
                              {f.department_details?.code || 'All Depts'}
                            </span>
                          </td>

                          <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                            {f.phone || '—'}
                          </td>

                          <td className="py-3 px-4">
                            {f.is_active ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                                <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                                Inactive
                              </span>
                            )}
                          </td>

                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleResendInvitation(f.id, fullName, f.email)}
                                disabled={actionInProgressId === f.id}
                                className="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                                title="Resend Account Activation Invitation"
                              >
                                <Send className="w-4 h-4" />
                              </button>

                              <button
                                onClick={() => handleOpenEditFaculty(f)}
                                className="p-1.5 text-slate-600 hover:text-primary-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                                title="Edit Faculty Details"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>

                              <button
                                onClick={() => handleToggleFacultyStatus(f.id, fullName)}
                                disabled={actionInProgressId === f.id}
                                className={`px-2.5 py-1 text-[11px] font-bold rounded-lg transition-colors cursor-pointer flex items-center gap-1 ${
                                  f.is_active
                                    ? 'text-rose-700 hover:bg-rose-50 border border-rose-200'
                                    : 'text-emerald-700 hover:bg-emerald-50 border border-emerald-200'
                                }`}
                                title={f.is_active ? 'Deactivate Faculty Access' : 'Activate Faculty Access'}
                              >
                                {f.is_active ? (
                                  <>
                                    <UserX className="w-3.5 h-3.5" />
                                    Deactivate
                                  </>
                                ) : (
                                  <>
                                    <UserCheck className="w-3.5 h-3.5" />
                                    Activate
                                  </>
                                )}
                              </button>

                              <button
                                onClick={() => handleDeleteFaculty(f.id, fullName)}
                                disabled={actionInProgressId === f.id}
                                className="p-1.5 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                                title="Permanently Delete Faculty Member"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
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
      )}

      {/* ========================================================= */}
      {/* TAB: STUDENT DIRECTORY */}
      {/* ========================================================= */}
      {activeTab === 'students' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-accent-600" />
                Student Enrollment Directory
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Verified undergraduate and postgraduate students enrolled with institutional @francisxavier.ac.in accounts.
              </p>
            </div>

            <div className="text-xs text-slate-500 font-semibold bg-slate-100 px-3 py-1.5 rounded-xl self-start sm:self-auto">
              Total Enrolled: <strong className="text-slate-900">{studentList.length}</strong>
            </div>
          </div>

          {/* Search & Filters */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row items-stretch md:items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
                placeholder="Search students by name, roll number, or email..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
              />
              {studentSearch && (
                <button
                  onClick={() => setStudentSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={studentDeptFilter}
                onChange={(e) => setStudentDeptFilter(e.target.value)}
                className="px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
              >
                <option value="">All Departments</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.code}>
                    {d.code} - {d.name}
                  </option>
                ))}
              </select>

              <select
                value={studentYearFilter}
                onChange={(e) => setStudentYearFilter(e.target.value)}
                className="px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
              >
                <option value="">All Academic Years</option>
                <option value="1">1st Year</option>
                <option value="2">2nd Year</option>
                <option value="3">3rd Year</option>
                <option value="4">4th Year</option>
              </select>
            </div>
          </div>

          {/* Student Table */}
          {loading && (!studentList || studentList.length === 0) ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : (!Array.isArray(studentList) || studentList.length === 0) ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500 space-y-3">
              <GraduationCap className="w-10 h-10 text-slate-300 mx-auto" />
              <p className="font-semibold">No students found matching your criteria.</p>
              <button
                onClick={() => {
                  setStudentSearch('');
                  setStudentDeptFilter('');
                  setStudentYearFilter('');
                }}
                className="text-primary-900 underline text-xs font-bold"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Student</th>
                      <th className="py-3 px-4">Institutional Email</th>
                      <th className="py-3 px-4">Register Number</th>
                      <th className="py-3 px-4">Department</th>
                      <th className="py-3 px-4">Year</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Joined</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {(Array.isArray(studentList) ? studentList : []).map((s) => {
                      const fullName = [s.first_name, s.last_name].filter(Boolean).join(' ') || s.username;
                      const initials = (fullName || 'S').slice(0, 2).toUpperCase();

                      return (
                        <tr key={s.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-accent-600/10 text-accent-700 flex items-center justify-center font-bold text-xs">
                                {initials}
                              </div>
                              <div>
                                <div className="font-bold text-slate-900">{fullName}</div>
                                <div className="text-[11px] text-slate-400 font-mono">@{s.username}</div>
                              </div>
                            </div>
                          </td>

                          <td className="py-3 px-4 font-mono text-slate-600">
                            <div className="flex items-center gap-1.5">
                              <span>{s.email}</span>
                              <span title="Institutional Domain Verified">
                                 <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                              </span>
                            </div>
                          </td>

                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-[11px] font-bold">
                              {s.register_number || '—'}
                            </span>
                          </td>

                          <td className="py-3 px-4">
                            <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-semibold text-[11px]">
                              {s.department_details?.code || '—'}
                            </span>
                          </td>

                          <td className="py-3 px-4">
                            <span className="px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 font-bold text-[11px]">
                              {s.year ? `Year ${s.year}` : '—'}
                            </span>
                          </td>

                          <td className="py-3 px-4">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              Active
                            </span>
                          </td>

                          <td className="py-3 px-4 text-slate-400 text-[11px] font-mono">
                            {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
                          </td>

                          <td className="py-3 px-4 text-right">
                            <button
                              type="button"
                              onClick={() => handleDeleteStudent(s.id, fullName)}
                              disabled={actionInProgressId === s.id}
                              className="p-1.5 rounded-lg text-rose-600 hover:text-rose-800 hover:bg-rose-50 transition border border-transparent hover:border-rose-200 cursor-pointer disabled:opacity-50"
                              title="Delete Student Record"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
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
      )}

      {/* ========================================================= */}
      {/* TAB: DEPARTMENT MASTER SYSTEM */}
      {/* ========================================================= */}
      {activeTab === 'departments' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-600" />
                Institutional Department Master
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Administer database-backed academic departments for student enrollment, faculty allocations, and course offerings.
              </p>
            </div>

            <button
              onClick={() => {
                setAddDeptError(null);
                setIsAddDeptModalOpen(true);
              }}
              className="px-4 py-2.5 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all cursor-pointer self-start sm:self-auto"
            >
              <Plus className="w-4 h-4" />
              Add Department
            </button>
          </div>

          {/* Search & Status Filters */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row items-stretch md:items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={deptSearch}
                onChange={(e) => setDeptSearch(e.target.value)}
                placeholder="Search departments by code or name..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
              />
              {deptSearch && (
                <button
                  onClick={() => setDeptSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={deptStatusFilter}
                onChange={(e) => setDeptStatusFilter(e.target.value)}
                className="px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
              >
                <option value="">All Statuses</option>
                <option value="true">Active Only</option>
                <option value="false">Inactive Only</option>
              </select>
            </div>
          </div>

          {/* Department Table */}
          {loading && (!adminDepartments || adminDepartments.length === 0) ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : (!Array.isArray(adminDepartments) || adminDepartments.length === 0) ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500 space-y-3">
              <Building2 className="w-10 h-10 text-slate-300 mx-auto" />
              <p className="font-semibold">No departments found matching your criteria.</p>
              <button
                onClick={() => {
                  setDeptSearch('');
                  setDeptStatusFilter('');
                }}
                className="text-primary-900 underline text-xs font-bold"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Code</th>
                      <th className="py-3 px-4">Department Name</th>
                      <th className="py-3 px-4">Description</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Created Date</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {adminDepartments.map((d) => (
                      <tr key={d.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-4">
                          <span className="px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 font-mono font-black text-xs">
                            {d.code}
                          </span>
                        </td>

                        <td className="py-3 px-4 font-bold text-slate-900">
                          {d.name}
                        </td>

                        <td className="py-3 px-4 text-slate-500 max-w-xs truncate">
                          {d.description || '—'}
                        </td>

                        <td className="py-3 px-4">
                          {d.is_active ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700">
                              <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                              Inactive
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                          {d.created_at ? new Date(d.created_at).toLocaleDateString() : '—'}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => handleToggleDeptStatus(d.id, d.code)}
                            disabled={actionInProgressId === d.id}
                            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition border cursor-pointer disabled:opacity-50 ${
                              d.is_active
                                ? 'bg-slate-50 text-rose-600 border-rose-200 hover:bg-rose-50'
                                : 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                            }`}
                            title={d.is_active ? 'Deactivate Department' : 'Activate Department'}
                          >
                            {d.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 1: COURSE PROPOSALS REVIEW */}
      {/* ========================================================= */}
      {activeTab === 'proposals' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              Pending Faculty Course Proposals Awaiting Institutional Approval
            </h2>
            <span className="text-xs text-slate-500">
              {pendingProposals.length} awaiting evaluation
            </span>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : pendingProposals.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500">
              No course proposals currently pending review. All faculty submissions have been evaluated.
            </div>
          ) : (
            <div className="space-y-4">
              {pendingProposals.map((course) => (
                <div key={course.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                          PENDING REVIEW
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                          {course.department?.code || 'Interdisciplinary'}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-primary-50 text-primary-900">
                          {course.level}
                        </span>
                      </div>
                      <h3 className="text-lg font-bold text-slate-900">{course.title}</h3>
                    </div>

                    <div className="text-right text-xs text-slate-500">
                      <div>Instructor: <strong>{course.instructor_name}</strong></div>
                      <div>Estimated: <strong>{course.estimated_hours} Hours</strong></div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">{course.description}</p>

                  {/* Modules list */}
                  {course.modules && course.modules.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
                      <span className="font-bold text-slate-700">Curriculum Structure ({course.modules.length} modules):</span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                        {course.modules.map((m) => (
                          <div key={m.id} className="text-[11px] text-slate-600">
                            • <strong>Module {m.order}:</strong> {m.title} ({m.duration_minutes}m)
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Review Actions */}
                  <div className="pt-2 flex flex-wrap items-center justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => handleDeleteCourse(course.id, course.title)}
                      disabled={actionInProgressId === course.id}
                      className="px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold border border-rose-200 flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                      title="Permanently Delete Proposal"
                    >
                      <Trash2 className="w-4 h-4 text-rose-600" />
                      Delete Proposal
                    </button>

                    <button
                      onClick={() => handleRejectProposal(course.id, course.title)}
                      disabled={actionInProgressId === course.id}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold border border-slate-300 flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      <XCircle className="w-4 h-4 text-slate-500" />
                      Reject with Notes
                    </button>

                    <button
                      onClick={() => handleApproveProposal(course.id, course.title)}
                      disabled={actionInProgressId === course.id}
                      className="px-5 py-2 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold shadow flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer"
                    >
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      {actionInProgressId === course.id ? 'Publishing...' : 'Approve & Publish to Catalogue'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB: ALL COURSES (INSTITUTIONAL CATALOGUE & PURGE) */}
      {/* ========================================================= */}
      {activeTab === 'all_courses' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Institutional Course Catalogue &amp; Deletion Management
              </h2>
              <p className="text-xs text-slate-500">
                Manage, audit, and permanently remove courses across all academic departments.
              </p>
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search course title or skill..."
                value={courseSearch}
                onChange={(e) => setCourseSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-white border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary-900"
              />
            </div>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : allCourses.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500">
              No courses found in institutional catalogue.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {allCourses
                .filter(c => !courseSearch || c.title.toLowerCase().includes(courseSearch.toLowerCase()) || c.skill?.name?.toLowerCase().includes(courseSearch.toLowerCase()))
                .map((course) => (
                  <div key={course.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          course.approval_status === 'APPROVED' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                          course.approval_status === 'PENDING_REVIEW' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                          'bg-slate-100 text-slate-700 border-slate-200'
                        }`}>
                          {course.approval_status}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {course.estimated_hours}h • {course.level}
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-slate-900 line-clamp-2 leading-snug">{course.title}</h3>
                      <p className="text-xs text-slate-500 line-clamp-2">{course.description}</p>
                      <div className="text-[11px] text-slate-400">
                        Instructor: <strong className="text-slate-700">{course.instructor_name}</strong>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                      <span className="text-[10px] text-slate-500">
                        {course.modules_count || course.modules?.length || 0} Modules
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteCourse(course.id, course.title)}
                        disabled={actionInProgressId === course.id}
                        className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold border border-rose-200 flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                        title="Delete Course Permanently"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                        Delete Course
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: AI SKILL SUGGESTIONS REVIEW */}
      {/* ========================================================= */}
      {activeTab === 'ai_suggestions' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              AI-Discovered Emerging Skills Pending Administrative Accreditation
            </h2>
            <span className="text-xs text-slate-500">
              {aiSuggestions.length} emerging competencies
            </span>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : aiSuggestions.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500">
              No AI skill suggestions currently pending review.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {aiSuggestions.map((sugg) => (
                <div key={sugg.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3 flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-amber-600" />
                        AI SUGGESTED
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {sugg.level}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-900">{sugg.title}</h3>
                    <p className="text-xs text-slate-600 leading-relaxed">{sugg.justification}</p>

                    <div className="text-[11px] text-slate-500 space-y-0.5 pt-2 border-t border-slate-100">
                      <div>Target Pillar: <strong>{sugg.category_name}</strong></div>
                      <div>Domain: <strong>{sugg.domain_name || 'General'}</strong></div>
                      {sugg.department_code && <div>Department: <strong>{sugg.department_code}</strong></div>}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => handleDeleteAiSuggestion(sugg.id, sugg.title)}
                      disabled={actionInProgressId === sugg.id}
                      className="px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold border border-rose-200 flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                      title="Delete AI Suggestion"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                      Delete
                    </button>
                    <button
                      onClick={() => {
                        setGeneratorSkillName(sugg.title);
                        setIsGeneratorOpen(true);
                      }}
                      className="px-3.5 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-bold shadow flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-accent-300" />
                      ⚡ Generate Full Course with AI
                    </button>
                    {sugg.approval_status === 'APPROVED' ? (
                      <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> Approved Skill
                      </span>
                    ) : (
                      <button
                        onClick={() => handleApproveAiSuggestion(sugg.id, sugg.title)}
                        disabled={actionInProgressId === sugg.id}
                        className="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold shadow flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        {actionInProgressId === sugg.id ? 'Promoting...' : 'Promote to Official Skill'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB: REPORTED VIDEOS REVIEW QUEUE */}
      {/* ========================================================= */}
      {activeTab === 'reported_videos' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Flag className="w-4 h-4 text-rose-600" />
                Student-Reported Video Issues &amp; Replacement Queue
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Review broken, deleted, or playback-disabled YouTube videos. Input replacement YouTube URLs or dismiss false reports.
              </p>
            </div>
            <span className="text-xs font-bold px-2.5 py-1 bg-rose-50 border border-rose-200 text-rose-800 rounded-full">
              {reportedVideos.length} Open Issues
            </span>
          </div>

          {loading ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : reportedVideos.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500 space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
              <div className="font-bold text-slate-700">All Video Resources Healthy</div>
              <p>No open video issues reported by students.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {reportedVideos.map((issue) => (
                <div key={issue.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200">
                          {issue.issue_type}
                        </span>
                        <span className="text-xs text-slate-500">
                          Reported by: <strong className="text-slate-800">{issue.student_username}</strong>
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">
                        {issue.video_title}
                      </h3>
                      <div className="text-xs text-slate-500">
                        Course: <strong className="text-slate-700">{issue.course_title}</strong> • Module: <strong className="text-slate-700">{issue.module_title}</strong>
                      </div>
                    </div>

                    <div className="text-right text-[11px] text-slate-400">
                      Reported: {new Date(issue.reported_at).toLocaleDateString()}
                    </div>
                  </div>

                  {issue.notes && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-0.5">
                      <span className="text-[10px] font-bold uppercase text-slate-400">Student Remarks:</span>
                      <p className="italic">"{issue.notes}"</p>
                    </div>
                  )}

                  {/* Resolution Controls */}
                  <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <div className="flex-grow max-w-md">
                      <input
                        type="url"
                        placeholder="Paste Replacement YouTube URL (e.g. https://www.youtube.com/watch?v=...)"
                        value={replacementUrls[issue.id] || ''}
                        onChange={(e) => setReplacementUrls(prev => ({ ...prev, [issue.id]: e.target.value }))}
                        className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-primary-600 bg-white"
                      />
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleDeleteReportedVideo(issue.id)}
                        disabled={actionInProgressId === issue.id}
                        className="p-2 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-xl transition-all cursor-pointer disabled:opacity-50"
                        title="Delete Reported Video Issue"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleResolveIssue(issue.id, 'DISMISS')}
                        disabled={actionInProgressId === issue.id}
                        className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
                      >
                        Dismiss
                      </button>
                      <button
                        type="button"
                        onClick={() => handleResolveIssue(issue.id, 'RESOLVE')}
                        disabled={actionInProgressId === issue.id}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow transition-all flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {actionInProgressId === issue.id ? 'Saving...' : 'Resolve & Update Video'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 3: SOURCE PROVENANCE LEDGER */}
      {/* ========================================================= */}
      {activeTab === 'provenance' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <h2 className="text-base font-bold text-slate-900">
              Institutional Source Provenance Ledger
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Every course and fact strictly maps to official FXEC links, prohibiting synthetic data.
            </p>
          </div>

          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-bold">
              <tr>
                <th className="p-3.5">Course Title</th>
                <th className="p-3.5">Department</th>
                <th className="p-3.5">Authority Type</th>
                <th className="p-3.5">Canonical Source URL</th>
                <th className="p-3.5">Last Verified</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {provenanceList.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/70">
                  <td className="p-3.5 font-bold text-slate-900">{item.title}</td>
                  <td className="p-3.5 text-slate-700">{item.department}</td>
                  <td className="p-3.5">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary-100 text-primary-900">
                      {item.source_type}
                    </span>
                  </td>
                  <td className="p-3.5">
                    {item.source_url ? (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary-700 hover:text-primary-900 underline flex items-center gap-1 truncate max-w-[200px]"
                      >
                        {item.source_url} <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-slate-400">PENDING_ADMIN_INPUT</span>
                    )}
                  </td>
                  <td className="p-3.5 text-slate-500">
                    {item.last_verified_at ? new Date(item.last_verified_at).toLocaleDateString() : 'Pending'}
                  </td>
                  <td className="p-3.5 text-right">
                    <button
                      onClick={() => handleVerifySource(item.id)}
                      disabled={actionInProgressId === item.id}
                      className="px-3 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-lg text-xs font-bold"
                    >
                      Verify
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 4: AUDIT LOGS */}
      {/* ========================================================= */}
      {activeTab === 'audit' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Security Audit Logs</h2>
              <p className="text-xs text-slate-500 mt-1">Administrative security actions and system activity trail.</p>
            </div>
            {auditLogs.length > 0 && (
              <button
                type="button"
                onClick={handleClearAuditLogs}
                className="px-3.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
                title="Clear All Audit Logs"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                Clear All Logs
              </button>
            )}
          </div>
          {auditLogs.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500">
              No audit log entries recorded.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-bold">
                  <tr>
                    <th className="p-3.5">User</th>
                    <th className="p-3.5">Action</th>
                    <th className="p-3.5">Resource</th>
                    <th className="p-3.5">Timestamp</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/70">
                      <td className="p-3.5 font-bold text-slate-900">{log.user}</td>
                      <td className="p-3.5 font-semibold text-primary-900">{log.action}</td>
                      <td className="p-3.5 text-slate-700">{log.resource_type} ({log.resource_id})</td>
                      <td className="p-3.5 text-slate-500">{new Date(log.timestamp).toLocaleString()}</td>
                      <td className="p-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleDeleteAuditLog(log.id)}
                          className="p-1.5 rounded-lg text-rose-600 hover:text-rose-800 hover:bg-rose-50 transition border border-transparent hover:border-rose-200 cursor-pointer"
                          title={`Delete audit log #${log.id}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 5: NOTIFICATION LOGS */}
      {/* ========================================================= */}
      {activeTab === 'email' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Notification Delivery Ledger</h2>
              <p className="text-xs text-slate-500 mt-1">Audit log of institutional dispatch messages and notifications.</p>
            </div>
            {emailLogs.length > 0 && (
              <button
                type="button"
                onClick={handleClearEmailLogs}
                className="px-3.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
                title="Clear All Notification Logs"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                Clear All Logs
              </button>
            )}
          </div>
          {emailLogs.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500">
              No notification ledger entries recorded.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-bold">
                  <tr>
                    <th className="p-3.5">Recipient</th>
                    <th className="p-3.5">Subject</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Sent At</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {emailLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/70">
                      <td className="p-3.5 font-bold text-slate-900">{log.recipient_email}</td>
                      <td className="p-3.5 text-slate-700">{log.subject}</td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          {log.status}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-500">{log.sent_at ? new Date(log.sent_at).toLocaleString() : 'Pending'}</td>
                      <td className="p-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleDeleteEmailLog(log.id)}
                          className="p-1.5 rounded-lg text-rose-600 hover:text-rose-800 hover:bg-rose-50 transition border border-transparent hover:border-rose-200 cursor-pointer"
                          title={`Delete notification log #${log.id}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 6: CERTIFICATES MANAGEMENT */}
      {/* ========================================================= */}
      {activeTab === 'certificates' && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Award className="w-5 h-5 text-amber-600" />
                  Institutional Certificate Registry
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  View, search, download, revoke, or regenerate accredited credentials.
                </p>
              </div>

              {/* Search input */}
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-80">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={certSearch}
                    onChange={(e) => setCertSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && fetchData()}
                    placeholder="Search ID, Student, Course, or Status..."
                    className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-xs focus:outline-hidden focus:border-primary-800"
                  />
                </div>
                <button
                  type="button"
                  onClick={fetchData}
                  className="px-4 py-2 bg-primary-900 text-white font-bold text-xs rounded-xl shadow-xs hover:bg-primary-800 cursor-pointer"
                >
                  Search
                </button>
              </div>
            </div>

            {/* Certificates Table */}
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 uppercase font-bold text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="p-3.5">Certificate ID</th>
                    <th className="p-3.5">Student</th>
                    <th className="p-3.5">Course &amp; Skill</th>
                    <th className="p-3.5">Score</th>
                    <th className="p-3.5">Issue Date</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {adminCerts.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500">
                        No certificates matching query found.
                      </td>
                    </tr>
                  ) : (
                    adminCerts.map((cert) => {
                      const isRevoked = cert.is_revoked || cert.status === 'REVOKED';
                      return (
                        <tr key={cert.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="p-3.5 font-mono font-bold text-[#0b1e3d]">
                            {cert.certificate_number}
                          </td>
                          <td className="p-3.5">
                            <div className="font-bold text-slate-900">{cert.student_name}</div>
                            <div className="text-[10px] text-slate-400">{cert.student_email || cert.student_username}</div>
                          </td>
                          <td className="p-3.5">
                            <div className="font-bold text-slate-800">{cert.course_title}</div>
                            <div className="text-[10px] text-primary-800 font-semibold">{cert.skill}</div>
                          </td>
                          <td className="p-3.5 font-bold text-slate-900">
                            {cert.score || 'Passed'}
                          </td>
                          <td className="p-3.5 text-slate-600">
                            {cert.issued_at ? new Date(cert.issued_at).toLocaleDateString() : 'Recorded'}
                          </td>
                          <td className="p-3.5">
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
                          <td className="p-3.5 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                type="button"
                                onClick={() => {
                                  setPreviewCert(cert);
                                  setIsPreviewOpen(true);
                                }}
                                className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
                                title="Preview Certificate"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>

                              <a
                                href={`/api/certificates/${cert.id}/pdf/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-1.5 rounded-lg bg-[#0b1e3d] text-white hover:bg-[#183664] transition"
                                title="Download PDF"
                              >
                                <Download className="w-3.5 h-3.5 text-[#d4af37]" />
                              </a>

                              {isRevoked ? (
                                <button
                                  type="button"
                                  onClick={() => handleRestoreCert(cert.id, cert.certificate_number)}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 hover:bg-emerald-100 font-bold text-[10px] transition"
                                  title="Restore Certificate"
                                >
                                  Restore
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => handleRevokeCert(cert.id, cert.certificate_number)}
                                  className="px-2.5 py-1 rounded-lg bg-rose-50 text-rose-800 hover:bg-rose-100 font-bold text-[10px] transition"
                                  title="Revoke Certificate"
                                >
                                  Revoke
                                </button>
                              )}

                              <button
                                type="button"
                                onClick={() => handleRegenerateCert(cert.id, cert.certificate_number)}
                                className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
                                title="Regenerate Certificate PDF & Hash"
                              >
                                <RotateCcw className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 7: BRANDING & CERTIFICATE CONFIGURATION */}
      {/* ========================================================= */}
      {activeTab === 'branding' && (
        <div className="space-y-8">
          {/* Section 1: Official Logo Assets Management */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Upload className="w-5 h-5 text-indigo-600" />
                Approved Institutional Branding Assets
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Manage active official logos and watermarks for certificates. AI logo modification is strictly disabled.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Asset 1: Horizontal Logo */}
              <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-4 flex flex-col justify-between">
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Top-Left Banner</span>
                  <h3 className="text-sm font-bold text-slate-900">Horizontal Institutional Logo</h3>
                  <div className="h-20 bg-white rounded-xl border border-slate-200 flex items-center justify-center p-2">
                    <img
                      src="/fxec_logo.png"
                      alt="Current Horizontal Logo"
                      className="max-h-full object-contain"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500">Active Approved Asset</p>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-primary-900 hover:text-primary-700 cursor-pointer bg-white px-3 py-2 rounded-xl border border-slate-200 text-center shadow-xs">
                    {uploadingAsset === 'HORIZONTAL_LOGO' ? 'Uploading...' : 'Replace Horizontal Logo'}
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileUpload('HORIZONTAL_LOGO', f);
                      }}
                    />
                  </label>
                </div>
              </div>

              {/* Asset 2: Circular Emblem */}
              <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-4 flex flex-col justify-between">
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Top-Right Seal</span>
                  <h3 className="text-sm font-bold text-slate-900">Circular FXEC Emblem</h3>
                  <div className="h-20 bg-white rounded-xl border border-slate-200 flex items-center justify-center p-2">
                    <img
                      src="/fxec_crest.png"
                      alt="Current Circular Emblem"
                      className="max-h-full object-contain rounded-full"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500">Active Approved Asset</p>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-primary-900 hover:text-primary-700 cursor-pointer bg-white px-3 py-2 rounded-xl border border-slate-200 text-center shadow-xs">
                    {uploadingAsset === 'CIRCULAR_EMBLEM' ? 'Uploading...' : 'Replace Circular Emblem'}
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileUpload('CIRCULAR_EMBLEM', f);
                      }}
                    />
                  </label>
                </div>
              </div>

              {/* Asset 3: Watermark */}
              <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/70 space-y-4 flex flex-col justify-between">
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Center Background</span>
                  <h3 className="text-sm font-bold text-slate-900">Campus / Institutional Watermark</h3>
                  <div className="h-20 bg-white rounded-xl border border-slate-200 flex items-center justify-center p-2 opacity-50">
                    <img
                      src="/fxec_crest.png"
                      alt="Watermark preview"
                      className="max-h-full object-contain"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500">Default: Subtle FXEC Emblem (0.08 opacity)</p>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-primary-900 hover:text-primary-700 cursor-pointer bg-white px-3 py-2 rounded-xl border border-slate-200 text-center shadow-xs">
                    {uploadingAsset === 'WATERMARK' ? 'Uploading...' : 'Upload Custom Watermark'}
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileUpload('WATERMARK', f);
                      }}
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Institutional Configuration Form */}
          {certConfig && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-primary-900" />
                  Institutional Certificate Details &amp; Signatories
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Configure college title, autonomous subtext, accreditation statements, and signatory lines without altering source code.
                </p>
              </div>

              {configSaved && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  Settings saved successfully!
                </div>
              )}

              <form onSubmit={handleSaveConfig} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Exact College Name
                    </label>
                    <input
                      type="text"
                      value={certConfig.institution_name}
                      onChange={(e) => setCertConfig({ ...certConfig, institution_name: e.target.value })}
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 font-semibold"
                      required
                    />
                    <p className="text-[10px] text-slate-400">Must be exact: FRANCIS XAVIER ENGINEERING COLLEGE</p>
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Institutional Subtext
                    </label>
                    <input
                      type="text"
                      value={certConfig.subtext}
                      onChange={(e) => setCertConfig({ ...certConfig, subtext: e.target.value })}
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                    <p className="text-[10px] text-slate-400">Default: (Autonomous)</p>
                  </div>

                  <div className="space-y-1.5 md:col-span-2">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Accreditation Statement
                    </label>
                    <input
                      type="text"
                      value={certConfig.accreditation_text}
                      onChange={(e) => setCertConfig({ ...certConfig, accreditation_text: e.target.value })}
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Signatory 1 Title
                    </label>
                    <input
                      type="text"
                      value={certConfig.signatory_1_title}
                      onChange={(e) => setCertConfig({ ...certConfig, signatory_1_title: e.target.value })}
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Signatory 1 Optional Name
                    </label>
                    <input
                      type="text"
                      value={certConfig.signatory_1_name || ''}
                      onChange={(e) => setCertConfig({ ...certConfig, signatory_1_name: e.target.value })}
                      placeholder="Leave blank unless verified"
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Signatory 2 Title
                    </label>
                    <input
                      type="text"
                      value={certConfig.signatory_2_title}
                      onChange={(e) => setCertConfig({ ...certConfig, signatory_2_title: e.target.value })}
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Signatory 2 Optional Name
                    </label>
                    <input
                      type="text"
                      value={certConfig.signatory_2_name || ''}
                      onChange={(e) => setCertConfig({ ...certConfig, signatory_2_name: e.target.value })}
                      placeholder="Leave blank unless verified"
                      className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    type="submit"
                    className="px-6 py-2.5 bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs rounded-xl shadow-sm transition cursor-pointer"
                  >
                    Save Institutional Configuration
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Autonomous AI Course Generator Modal */}
      <AICourseGeneratorModal
        isOpen={isGeneratorOpen}
        onClose={() => setIsGeneratorOpen(false)}
        defaultSkillName={generatorSkillName}
        onSuccess={() => {
          fetchData();
        }}
      />

      {/* Admin Certificate Preview Modal */}
      <CertificatePreviewModal
        certificate={previewCert}
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        studentNameFallback={previewCert?.student_name}
      />

      {/* ========================================================= */}
      {/* MODAL: ADD FACULTY MEMBER */}
      {/* ========================================================= */}
      {isAddFacultyModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-100 my-8 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-primary-900 bg-primary-50 px-2.5 py-0.5 rounded-full">
                  Institutional Provisioning
                </span>
                <h3 className="text-lg font-black text-slate-900 mt-1">Add New Faculty Member</h3>
                <p className="text-xs text-slate-500">Official faculty credentials.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsAddFacultyModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg text-sm"
              >
                ✕
              </button>
            </div>

            {addFacultyError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold rounded-xl flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{addFacultyError}</span>
              </div>
            )}

            <form onSubmit={handleAddFacultySubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">First Name *</label>
                  <input
                    type="text"
                    required
                    value={addFacultyForm.first_name}
                    onChange={(e) => setAddFacultyForm({ ...addFacultyForm, first_name: e.target.value })}
                    placeholder="e.g. Senthil"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Last Name</label>
                  <input
                    type="text"
                    value={addFacultyForm.last_name}
                    onChange={(e) => setAddFacultyForm({ ...addFacultyForm, last_name: e.target.value })}
                    placeholder="e.g. Kumar"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Official Faculty Email *
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    required
                    value={addFacultyForm.email}
                    onChange={(e) => setAddFacultyForm({ ...addFacultyForm, email: e.target.value })}
                    placeholder="Enter faculty email address"
                    className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 font-mono text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Faculty ID *</label>
                  <input
                    type="text"
                    required
                    value={addFacultyForm.faculty_id}
                    onChange={(e) => setAddFacultyForm({ ...addFacultyForm, faculty_id: e.target.value.toUpperCase() })}
                    placeholder="e.g. FX-CSE-102"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Department *</label>
                  <select
                    required
                    value={addFacultyForm.department}
                    onChange={(e) => setAddFacultyForm({ ...addFacultyForm, department: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
                  >
                    <option value="">Select Department</option>
                    {departments.length === 0 ? (
                      <option value="" disabled>No departments available — add in Departments tab</option>
                    ) : (
                      departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.code} - {d.name}
                        </option>
                      ))
                    )}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Phone Number (Optional)</label>
                  <div className="relative">
                    <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="tel"
                      value={addFacultyForm.phone}
                      onChange={(e) => setAddFacultyForm({ ...addFacultyForm, phone: e.target.value })}
                      placeholder="+91 9876543210"
                      className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Temporary Initial Password</label>
                  <div className="relative">
                    <Key className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="password"
                      value={addFacultyForm.password}
                      onChange={(e) => setAddFacultyForm({ ...addFacultyForm, password: e.target.value })}
                      placeholder="Leave blank for institutional default"
                      className="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="addFacultyActive"
                  checked={addFacultyForm.is_active}
                  onChange={(e) => setAddFacultyForm({ ...addFacultyForm, is_active: e.target.checked })}
                  className="rounded border-slate-300 text-primary-900 focus:ring-primary-900"
                />
                <label htmlFor="addFacultyActive" className="font-semibold text-slate-700 cursor-pointer">
                  Activate account immediately upon creation
                </label>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddFacultyModalOpen(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addFacultyLoading}
                  className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 text-white rounded-xl font-bold flex items-center gap-2 shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {addFacultyLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Provisioning...
                    </>
                  ) : (
                    <>
                      <UserPlus className="w-3.5 h-3.5" />
                      Create Faculty Member
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: EDIT FACULTY MEMBER */}
      {/* ========================================================= */}
      {editingFaculty && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl border border-slate-100 my-8 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                  Faculty Administration
                </span>
                <h3 className="text-lg font-black text-slate-900 mt-1">Edit Faculty Member</h3>
                <p className="text-xs text-slate-500 font-mono">{editingFaculty.email}</p>
              </div>
              <button
                type="button"
                onClick={() => setEditingFaculty(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg text-sm"
              >
                ✕
              </button>
            </div>

            {editFacultyError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold rounded-xl flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{editFacultyError}</span>
              </div>
            )}

            <form onSubmit={handleEditFacultySubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">First Name *</label>
                  <input
                    type="text"
                    required
                    value={editFacultyForm.first_name}
                    onChange={(e) => setEditFacultyForm({ ...editFacultyForm, first_name: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Last Name</label>
                  <input
                    type="text"
                    value={editFacultyForm.last_name}
                    onChange={(e) => setEditFacultyForm({ ...editFacultyForm, last_name: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Faculty ID</label>
                  <input
                    type="text"
                    value={editFacultyForm.faculty_id}
                    onChange={(e) => setEditFacultyForm({ ...editFacultyForm, faculty_id: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Department *</label>
                  <select
                    required
                    value={editFacultyForm.department}
                    onChange={(e) => setEditFacultyForm({ ...editFacultyForm, department: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-hidden focus:border-primary-900"
                  >
                    <option value="">Select Department</option>
                    {departments.length === 0 ? (
                      <option value="" disabled>No departments available — add in Departments tab</option>
                    ) : (
                      departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.code} - {d.name}
                        </option>
                      ))
                    )}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Phone Number</label>
                  <input
                    type="tel"
                    value={editFacultyForm.phone}
                    onChange={(e) => setEditFacultyForm({ ...editFacultyForm, phone: e.target.value })}
                    placeholder="+91 9876543210"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Reset Password (Optional)</label>
                  <input
                    type="password"
                    value={editFacultyForm.password}
                    onChange={(e) => setEditFacultyForm({ ...editFacultyForm, password: e.target.value })}
                    placeholder="Leave blank to keep current"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                  />
                </div>
              </div>

              <div className="pt-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="editFacultyActive"
                  checked={editFacultyForm.is_active}
                  onChange={(e) => setEditFacultyForm({ ...editFacultyForm, is_active: e.target.checked })}
                  className="rounded border-slate-300 text-primary-900 focus:ring-primary-900"
                />
                <label htmlFor="editFacultyActive" className="font-semibold text-slate-700 cursor-pointer">
                  Faculty Account is Active
                </label>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setEditingFaculty(null)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editFacultyLoading}
                  className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 text-white rounded-xl font-bold flex items-center gap-2 shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {editFacultyLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* ========================================================= */}
      {/* MODAL: ADD DEPARTMENT */}
      {/* ========================================================= */}
      {isAddDeptModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-slate-100 my-8 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                  Department Master
                </span>
                <h3 className="text-lg font-black text-slate-900 mt-1">Add Academic Department</h3>
                <p className="text-xs text-slate-500">Create a permanent institutional department in the database.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsAddDeptModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg text-sm"
              >
                ✕
              </button>
            </div>

            {addDeptError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold rounded-xl flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{addDeptError}</span>
              </div>
            )}

            <form onSubmit={handleAddDeptSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Department Code *
                </label>
                <input
                  type="text"
                  required
                  value={addDeptForm.code}
                  onChange={(e) => setAddDeptForm({ ...addDeptForm, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. CSE, ECE, AIDS"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 font-mono uppercase"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Department Name *
                </label>
                <input
                  type="text"
                  required
                  value={addDeptForm.name}
                  onChange={(e) => setAddDeptForm({ ...addDeptForm, name: e.target.value })}
                  placeholder="e.g. Computer Science and Engineering"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Description (Optional)
                </label>
                <textarea
                  rows={3}
                  value={addDeptForm.description}
                  onChange={(e) => setAddDeptForm({ ...addDeptForm, description: e.target.value })}
                  placeholder="Brief description of the academic department..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900"
                />
              </div>

              <div className="pt-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="addDeptActive"
                  checked={addDeptForm.is_active}
                  onChange={(e) => setAddDeptForm({ ...addDeptForm, is_active: e.target.checked })}
                  className="rounded border-slate-300 text-primary-900 focus:ring-primary-900"
                />
                <label htmlFor="addDeptActive" className="font-semibold text-slate-700 cursor-pointer">
                  Department is active and available for student registration
                </label>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddDeptModalOpen(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addDeptLoading}
                  className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 text-white rounded-xl font-bold flex items-center gap-2 shadow-sm transition-all disabled:opacity-50 cursor-pointer"
                >
                  {addDeptLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-3.5 h-3.5" />
                      Create Department
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
