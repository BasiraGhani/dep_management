import { useQuery } from '@tanstack/react-query';

import { getDashboard } from '../api/dashboard';

export const dashboardKeys = {
  all: ['dashboard'] as const,
};

/**
 * The signed-in user's dashboard; the payload's `role` says which shape it is.
 *
 * Refetched whenever the dashboard is opened: almost any change elsewhere
 * (a new student, course or grade) changes a figure, and the request is cheap.
 */
export function useDashboardQuery() {
  return useQuery({ queryKey: dashboardKeys.all, queryFn: getDashboard, refetchOnMount: 'always' });
}
