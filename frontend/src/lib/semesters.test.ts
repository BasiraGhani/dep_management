import { describe, expect, it } from 'vitest';

import { compareSemesters, currentSemester, semesterOptions } from './semesters';

describe('semesters', () => {
  it.each([
    ['2026-01-15', '2026-Spring'],
    ['2026-05-31', '2026-Spring'],
    ['2026-06-01', '2026-Summer'],
    ['2026-08-31', '2026-Summer'],
    ['2026-09-01', '2026-Fall'],
    ['2026-12-31', '2026-Fall'],
  ])('%s is in %s', (day, semester) => {
    expect(currentSemester(new Date(`${day}T12:00:00`))).toBe(semester);
  });

  it('offers last, this and next year in calendar order', () => {
    expect(semesterOptions(new Date('2026-11-24T12:00:00'))).toEqual([
      '2025-Spring',
      '2025-Summer',
      '2025-Fall',
      '2026-Spring',
      '2026-Summer',
      '2026-Fall',
      '2027-Spring',
      '2027-Summer',
      '2027-Fall',
    ]);
  });

  it('compares semesters in calendar order', () => {
    const shuffled = ['2026-Fall', '2025-Fall', '2026-Spring', '2026-Summer', '2025-Spring'];
    expect([...shuffled].sort(compareSemesters)).toEqual([
      '2025-Spring',
      '2025-Fall',
      '2026-Spring',
      '2026-Summer',
      '2026-Fall',
    ]);
  });
});
