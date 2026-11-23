import { useQuery } from '@tanstack/react-query';

import { getMe } from '../api/auth';

/** Query key of the logged-in user; includes the token so a new login refetches. */
export function currentUserKey(token: string | null) {
  return ['auth', 'me', token] as const;
}

/** GET /auth/me for the given token (disabled while logged out). */
export function useCurrentUserQuery(token: string | null) {
  return useQuery({
    queryKey: currentUserKey(token),
    queryFn: getMe,
    enabled: token !== null,
    staleTime: 5 * 60_000,
  });
}
