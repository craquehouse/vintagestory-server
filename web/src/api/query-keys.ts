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
    lookup: (slug: string) => ['mods', 'lookup', slug] as const,
  },
  server: {
    status: ['server', 'status'] as const,
    installStatus: ['server', 'install', 'status'] as const,
  },
  config: {
    files: ['config', 'files'] as const,
    file: (name: string) => ['config', 'files', name] as const,
    // Game settings (Story 6.4)
    game: ['config', 'game'] as const,
    // API settings (Story 6.4)
    api: ['config', 'api'] as const,
  },
};
