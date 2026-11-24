import { Route, Routes } from 'react-router';

import { PAGE_ACCESS } from './auth/access';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { RoleGate } from './auth/RoleGate';
import { ComingSoon } from './components/ComingSoon';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { DepartmentDetailPage } from './pages/DepartmentDetailPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { StudentsPage } from './pages/StudentsPage';
import { TeacherDetailPage } from './pages/TeacherDetailPage';
import { TeachersPage } from './pages/TeachersPage';

/**
 * Every route of ARCHITECTURE §4. Pages not built yet show a placeholder naming
 * the task that builds them. Role rules come from PAGE_ACCESS.
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />

          <Route path="departments" element={<DepartmentsPage />} />
          <Route path="departments/:id" element={<DepartmentDetailPage />} />
          <Route path="teachers" element={<TeachersPage />} />
          <Route path="teachers/:id" element={<TeacherDetailPage />} />
          <Route path="courses" element={<ComingSoon title="Courses" task="T6.4" />} />
          <Route path="courses/:id" element={<ComingSoon title="Course" task="T6.4" />} />
          <Route path="profile" element={<ComingSoon title="My profile" task="T7.3" />} />

          <Route element={<RoleGate roles={PAGE_ACCESS.students} />}>
            <Route path="students" element={<StudentsPage />} />
            <Route path="students/:id" element={<StudentDetailPage />} />
          </Route>
          <Route element={<RoleGate roles={PAGE_ACCESS.gradeEntry} />}>
            <Route
              path="courses/:id/grades"
              element={<ComingSoon title="Grade entry" task="T7.2" />}
            />
          </Route>
          <Route element={<RoleGate roles={PAGE_ACCESS.users} />}>
            <Route path="users" element={<ComingSoon title="User management" task="T7.3" />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
