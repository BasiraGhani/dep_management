import { afterEach, describe, expect, it } from 'vitest';

import { stubApi } from '../test/apiStub';
import { changePassword, getMe, login } from './auth';
import { getCourse, listCourses, setCourseGrades } from './courses';
import { getDashboard } from './dashboard';
import { deleteDepartment, listDepartments, updateDepartment } from './departments';
import { enroll, listEnrollments, setGrade, unenroll } from './enrollments';
import { exportCsv } from './export';
import { createStudent, listStudents } from './students';
import { listTeachers, updateTeacher } from './teachers';
import { deleteUser, listUsers, resetPassword } from './users';

let stub: ReturnType<typeof stubApi> | undefined;
afterEach(() => stub?.restore());

describe('API modules call the documented endpoints', () => {
  it('login posts an OAuth2 password form', async () => {
    stub = stubApi(200, { access_token: 'tok', token_type: 'bearer' });

    const token = await login('demo.hod', 'demo-password');

    const call = stub.calls[0];
    expect([call.method, call.url]).toEqual(['POST', '/auth/login']);
    expect(call.data).toBe('username=demo.hod&password=demo-password');
    expect(token.access_token).toBe('tok');
  });

  it.each([
    ['getMe', () => getMe(), 'GET', '/auth/me'],
    ['getDashboard', () => getDashboard(), 'GET', '/dashboard'],
    ['getCourse', () => getCourse(7), 'GET', '/courses/7'],
    ['deleteDepartment', () => deleteDepartment(3), 'DELETE', '/departments/3'],
    ['unenroll', () => unenroll(9), 'DELETE', '/enrollments/9'],
    ['resetPassword', () => resetPassword(4), 'POST', '/users/4/reset-password'],
    ['deleteUser', () => deleteUser(4), 'DELETE', '/users/4'],
  ])('%s', async (_name, call, method, url) => {
    stub = stubApi();
    await call();
    expect([stub.calls[0].method, stub.calls[0].url]).toEqual([method, url]);
  });

  it('list functions pass search, paging and filters as query parameters', async () => {
    stub = stubApi(200, { items: [], total: 0 });

    await listDepartments({ search: 'cs', skip: 20, limit: 10 });
    await listTeachers({ department_id: 2, title: 'professor' });
    await listStudents({ year: 2, status: 'active' });
    await listCourses({ teacher_id: 5 });
    await listEnrollments({ semester: '2026-Fall' });
    await listUsers({ role: 'admin', is_active: true });

    expect(stub.calls.map((c) => [c.url, c.params])).toEqual([
      ['/departments', { search: 'cs', skip: 20, limit: 10 }],
      ['/teachers', { department_id: 2, title: 'professor' }],
      ['/students', { year: 2, status: 'active' }],
      ['/courses', { teacher_id: 5 }],
      ['/enrollments', { semester: '2026-Fall' }],
      ['/users', { role: 'admin', is_active: true }],
    ]);
  });

  it('writes send JSON bodies with the right method', async () => {
    stub = stubApi();

    await changePassword({ current_password: 'old-pass-1', new_password: 'new-pass-1' });
    await updateDepartment(1, { building: 'North' });
    await updateTeacher(2, { phone: null });
    await createStudent({
      student_no: 'S1',
      first_name: 'A',
      last_name: 'B',
      email: 'a@b.co',
      department_id: 1,
      year: 1,
    });
    await enroll({ student_id: 1, course_id: 2, semester: '2026-Fall' });
    await setGrade(5, 'B+');
    await setGrade(5, null);
    await setCourseGrades(2, [{ enrollment_id: 5, grade: 'A' }]);

    expect(stub.calls.map((c) => [c.method, c.url, JSON.parse(String(c.data)) as unknown])).toEqual(
      [
        [
          'POST',
          '/auth/change-password',
          { current_password: 'old-pass-1', new_password: 'new-pass-1' },
        ],
        ['PATCH', '/departments/1', { building: 'North' }],
        ['PATCH', '/teachers/2', { phone: null }],
        [
          'POST',
          '/students',
          {
            student_no: 'S1',
            first_name: 'A',
            last_name: 'B',
            email: 'a@b.co',
            department_id: 1,
            year: 1,
          },
        ],
        ['POST', '/enrollments', { student_id: 1, course_id: 2, semester: '2026-Fall' }],
        ['PATCH', '/enrollments/5/grade', { grade: 'B+' }],
        ['PATCH', '/enrollments/5/grade', { grade: null }],
        ['PUT', '/courses/2/grades', [{ enrollment_id: 5, grade: 'A' }]],
      ],
    );
  });

  it('exportCsv downloads a blob with the filters', async () => {
    const csv = new Blob(['id,code\n1,CS101\n'], { type: 'text/csv' });
    stub = stubApi(200, csv);

    const file = await exportCsv('courses', { department_id: 1, search: 'cs' });

    const call = stub.calls[0];
    expect([call.url, call.params, call.responseType]).toEqual([
      '/export/courses.csv',
      { department_id: 1, search: 'cs' },
      'blob',
    ]);
    expect(file).toEqual({ filename: 'courses.csv', blob: csv });
  });
});
