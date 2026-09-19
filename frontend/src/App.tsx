import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { CataloguePage } from './pages/CataloguePage';
import { CourseDetail } from './pages/CourseDetail';
import { CourseViewer } from './pages/CourseViewer';
import { SkillGapAnalysis } from './pages/SkillGapAnalysis';
import { AssessmentPreflight } from './pages/AssessmentPreflight';
import { AssessmentSession } from './pages/AssessmentSession';
import { AssessmentResult } from './pages/AssessmentResult';
import { CertificateVerify } from './pages/CertificateVerify';
import { DashboardPage } from './pages/DashboardPage';
import { MentorPage } from './pages/MentorPage';
import { AdminPage } from './pages/AdminPage';
import { GoogleCallback } from './pages/GoogleCallback';
import { ModuleLearningView } from './pages/ModuleLearningView';
import { FacultyActivationPage } from './pages/FacultyActivationPage';

// Protected Route Component for Auth
const ProtectedRoute: React.FC<{ children: React.ReactNode; allowedRoles?: string[] }> = ({
  children,
  allowedRoles,
}) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <div className="flex flex-col min-h-screen">
          <Navbar />
          <main className="flex-grow">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<Home />} />
              <Route path="/catalogue" element={<CataloguePage />} />
              <Route path="/course/:slug" element={<CourseDetail />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/auth/google/callback" element={<GoogleCallback />} />
              <Route path="/activate-faculty/:token" element={<FacultyActivationPage />} />
              <Route path="/activate-faculty" element={<FacultyActivationPage />} />
              <Route path="/verify-certificate/:certificateId" element={<CertificateVerify />} />
              <Route path="/verify/:certificateId" element={<CertificateVerify />} />

              {/* Student & Learning Routes */}
              <Route
                path="/learn/:slug"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <CourseViewer />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/courses/:courseId/modules/:moduleId"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <ModuleLearningView />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/learn/:slug/modules/:moduleId"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <ModuleLearningView />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/skill-gap/:courseId"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <SkillGapAnalysis />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/assessments/:assessmentId/preflight"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <AssessmentPreflight />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/assessments/:assessmentId/session"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <AssessmentSession />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/assessments/:attemptId/result"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'FACULTY', 'MENTOR', 'ADMIN']}>
                    <AssessmentResult />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT']}>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />

              {/* Faculty & Administrative Routes */}
              <Route
                path="/faculty"
                element={
                  <ProtectedRoute allowedRoles={['FACULTY', 'MENTOR', 'ADMIN']}>
                    <MentorPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/mentor"
                element={
                  <ProtectedRoute allowedRoles={['FACULTY', 'MENTOR', 'ADMIN']}>
                    <MentorPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <AdminPage />
                  </ProtectedRoute>
                }
              />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </AuthProvider>
  );
};

export default App;
