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
