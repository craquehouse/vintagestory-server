/**
 * Hook for fetching the current authenticated user's information.
 *
 * Uses the /api/v1alpha1/auth/me endpoint to get the user's role.
 * This is useful for checking permissions and displaying user information.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { queryKeys } from '../query-keys';
import type { ApiResponse } from '../types';

/**
 * Response data from the auth/me endpoint.
 */
export interface AuthMeData {
  role: string;
}

/**
 * Full response from the auth/me endpoint (after camelCase transformation).
 */
export type AuthMeResponse = ApiResponse<AuthMeData>;

/**
 * Fetch the current user's authentication information.
 *
 * Uses TanStack Query for caching and automatic refetching.
 * The role won't change during a session, so staleTime is set to Infinity.
 *
 * @example
 * function UserProfile() {
 *   const { data, isLoading, error } = useAuthMe();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return <div>Role: {data?.data.role}</div>;
 * }
 */
export function useAuthMe() {
  return useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: () => apiClient<AuthMeResponse>('/api/v1alpha1/auth/me'),
    // Role won't change during session, so keep it cached indefinitely
    staleTime: Infinity,
  });
}

/**
 * Whether the key is Admin, for role-gated controls (Story 23.3, Epic 23 ADR-6 decision 3).
 *
 * - `isAdmin`: the role is known to be Admin
 * - `isKnown`: a role was returned (Admin or not)
 * - `isError`: the role could not be loaded
 *
 * While loading, all three are false, so a control that needs Admin stays disabled
 * until the role is known. The API enforces the role either way.
 */
export function useIsAdmin(): { isAdmin: boolean; isKnown: boolean; isError: boolean } {
  const { data, isError } = useAuthMe();
  const role = data?.data?.role;
  return {
    isAdmin: role === 'admin',
    isKnown: typeof role === 'string',
    isError,
  };
}
