/** Semesters are "YYYY-Spring", "YYYY-Summer" or "YYYY-Fall" (ARCHITECTURE §2). */

const SEASONS = ['Spring', 'Summer', 'Fall'] as const;

/** The semester `date` falls in: Jan–May Spring, Jun–Aug Summer, Sep–Dec Fall. */
export function currentSemester(date = new Date()): string {
  const month = date.getMonth(); // 0 = January
  const season = month <= 4 ? 'Spring' : month <= 7 ? 'Summer' : 'Fall';
  return `${String(date.getFullYear())}-${season}`;
}

/** Last year, this year and next year, in calendar order. */
export function semesterOptions(date = new Date()): string[] {
  const year = date.getFullYear();
  return [year - 1, year, year + 1].flatMap((y) => SEASONS.map((s) => `${String(y)}-${s}`));
}
