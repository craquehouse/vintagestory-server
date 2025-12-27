/**
 * Centralized query key definitions for TanStack Query.
 *
 * Using a structured object for query keys provides:
 * - Type safety for cache invalidation
 * - Consistent key patterns across the application
 * - Easy refactoring when endpoints change
 */

export const queryKeys = {
  auth: {
    me: ['auth', 'me'] as const,
  },
  mods: {
    all: ['mods'] as const,
    detail: (slug: string) => ['mods', slug] as const,
  },
  server: {
    status: ['server', 'status'] as const,
  },
  config: {
    files: ['config', 'files'] as const,
    file: (name: string) => ['config', 'files', name] as const,
  },
};
