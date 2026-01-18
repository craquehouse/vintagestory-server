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
    browse: (params: {
      page?: number;
      pageSize?: number;
      sort?: string;
      search?: string;
    }) => ['mods', 'browse', params] as const,
  },
  server: {
    status: ['server', 'status'] as const,
    installStatus: ['server', 'install', 'status'] as const,
  },
  config: {
    // Directory listing - supports optional directory param for nested browsing (Story 9.7)
    directories: (directory?: string) =>
      directory
        ? (['config', 'directories', directory] as const)
        : (['config', 'directories'] as const),
    // File listing - supports optional directory param (Story 9.7)
    files: (directory?: string) =>
      directory
        ? (['config', 'files', directory] as const)
        : (['config', 'files'] as const),
    file: (name: string) => ['config', 'files', 'content', name] as const,
    // Game settings (Story 6.4)
    game: ['config', 'game'] as const,
    // API settings (Story 6.4)
    api: ['config', 'api'] as const,
  },
  console: {
    logs: ['console', 'logs'] as const,
  },
  jobs: {
    all: ['jobs'] as const,
  },
  // Story 13.2: Version management
  versions: {
    all: (channel?: string) =>
      channel ? (['versions', channel] as const) : (['versions'] as const),
    detail: (version: string) => ['versions', 'detail', version] as const,
  },
  // Story 12.4: Dashboard metrics
  metrics: {
    current: ['metrics', 'current'] as const,
    history: (minutes?: number) =>
      minutes !== undefined
        ? (['metrics', 'history', minutes] as const)
        : (['metrics', 'history'] as const),
  },
};
