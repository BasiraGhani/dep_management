import { createRoutesFromElements, Route, type RouteObject } from 'react-router';

import { PAGE_ACCESS } from './auth/access';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { RoleGate } from './auth/RoleGate';
import { Layout } from './components/Layout';
import { CourseDetailPage } from './pages/CourseDetailPage';
import { CoursesPage } from './pages/CoursesPage';
import { DashboardPage } from './pages/DashboardPage';
import { DepartmentDetailPage } from './pages/DepartmentDetailPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { GradeEntryPage } from './pages/GradeEntryPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProfilePage } from './pages/ProfilePage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { StudentsPage } from './pages/StudentsPage';
import { TeacherDetailPage } from './pages/TeacherDetailPage';
import { TeachersPage } from './pages/TeachersPage';
import { UsersPage } from './pages/UsersPage';

/**
 * Every route of ARCHITECTURE §4. Role rules come from PAGE_ACCESS.
 *
 * Used with a data router (createBrowserRouter; createMemoryRouter in tests), so
 * pages can use useBlocker to warn about unsaved changes.
 */
export const appRoutes: RouteObject[] = createRoutesFromElements(
  <>
    <Route path="/login" element={<LoginPage />} />

    <Route element={<ProtectedRoute />}>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />

        <Route path="departments" element={<DepartmentsPage />} />
        <Route path="departments/:id" element={<DepartmentDetailPage />} />
        <Route path="teachers" element={<TeachersPage />} />
        <Route path="teachers/:id" element={<TeacherDetailPage />} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="courses/:id" element={<CourseDetailPage />} />
        <Route path="profile" element={<ProfilePage />} />

        <Route element={<RoleGate roles={PAGE_ACCESS.students} />}>
          <Route path="students" element={<StudentsPage />} />
          <Route path="students/:id" element={<StudentDetailPage />} />
        </Route>
        <Route element={<RoleGate roles={PAGE_ACCESS.gradeEntry} />}>
          <Route path="courses/:id/grades" element={<GradeEntryPage />} />
        </Route>
        <Route element={<RoleGate roles={PAGE_ACCESS.users} />}>
          <Route path="users" element={<UsersPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Route>
  </>,
);
