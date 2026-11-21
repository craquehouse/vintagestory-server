/**
 * Story 25.2: Game Settings warns about a wrong path (FR348, Epic 25 ADR-3).
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { queryKeys } from '@/api/query-keys';
import type { ServerConfigPathCheck, ServerConfigPathEntry } from '@/api/types';
import {
  ServerConfigPathsWarning,
  pathProblem,
  pathProblemLines,
} from './ServerConfigPathsWarning';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

const OK_SAVE = {
  given: null,
  resolved: '/data/serverdata/Saves/default.vcdbs',
  status: 'ok',
  problem: false,
};

/** The API's snake_case answer. */
function apiCheck(overrides: Record<string, unknown> = {}) {
  return {
    status: 'ok',
    data: {
      mod_paths: [
        { given: 'Mods', resolved: '/data/server/Mods', status: 'ok', problem: false },
        {
          given: '/data/serverdata/Mods',
          resolved: '/data/serverdata/Mods',
          status: 'ok',
          problem: false,
        },
      ],
      save_file: OK_SAVE,
      manager_mods_folder: '/data/serverdata/Mods',
      manager_mods_folder_listed: true,
      ...overrides,
    },
  };
}

function answer(body: unknown, ok = true, status = 200) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  });
}

function renderWarning(role: string | null = 'admin') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (role) {
    queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role } });
  }
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  render(<ServerConfigPathsWarning />, { wrapper: Wrapper });
  return queryClient;
}

function entry(overrides: Partial<ServerConfigPathEntry>): ServerConfigPathEntry {
  return { given: 'x', resolved: '/data/server/x', status: 'missing', problem: true, ...overrides };
}

function camelCheck(overrides: Partial<ServerConfigPathCheck> = {}): ServerConfigPathCheck {
  return {
    modPaths: [],
    saveFile: { given: null, resolved: '/s', status: 'ok', problem: false },
    managerModsFolder: '/data/serverdata/Mods',
    managerModsFolderListed: true,
    ...overrides,
  };
}

describe('pathProblem', () => {
  it.each([
    ['missing', 'mod', 'does not exist'],
    ['missing', 'save', 'its folder does not exist, so the game server will not start'],
    ['not_a_directory', 'mod', 'is a file, not a folder'],
    ['not_a_file', 'save', 'is a folder, not a file'],
    ['not_readable', 'mod', 'cannot be read by the game server'],
    ['not_writable', 'save', 'cannot be written by the game server'],
    ['invalid', 'mod', 'is not a usable path'],
  ] as const)('%s (%s): %s', (status, kind, text) => {
    expect(pathProblem(entry({ status }), kind)).toBe(text);
  });
});

describe('pathProblemLines', () => {
  it('has no line when nothing is a problem', () => {
    const check = camelCheck({
      modPaths: [entry({ status: 'not_installed', problem: false })],
      saveFile: { given: null, resolved: '/s', status: 'not_created_yet', problem: false },
    });

    expect(pathProblemLines(check)).toEqual([]);
  });

  it('names a mod path as written and as resolved', () => {
    const check = camelCheck({
      modPaths: [
        entry({ given: '../data/serverdata/Mods', resolved: '/data/data/serverdata/Mods' }),
      ],
    });

    expect(pathProblemLines(check)).toEqual([
      'Mod folder "../data/serverdata/Mods" (/data/data/serverdata/Mods) does not exist.',
    ]);
  });

  it('does not repeat a path that resolves to itself', () => {
    const check = camelCheck({
      modPaths: [entry({ given: '/nowhere', resolved: '/nowhere' })],
    });

    expect(pathProblemLines(check)).toEqual(['Mod folder "/nowhere" does not exist.']);
  });

  it('explains invalid ModPaths', () => {
    const check = camelCheck({
      modPaths: [{ given: null, resolved: null, status: 'invalid', problem: true }],
    });

    expect(pathProblemLines(check)[0]).toBe('ModPaths is not a list of folder names.');
  });

  it('names the manager mods folder when ModPaths leaves it out', () => {
    const check = camelCheck({ managerModsFolderListed: false });

    expect(pathProblemLines(check)).toEqual([
      'ModPaths does not include /data/serverdata/Mods, where the manager installs mods, so the game loads none of them.',
    ]);
  });

  it('names the save file and why the server will not start', () => {
    const check = camelCheck({
      saveFile: {
        given: 'worlds/a.vcdbs',
        resolved: '/data/worlds/a.vcdbs',
        status: 'missing',
        problem: true,
      },
    });

    expect(pathProblemLines(check)).toEqual([
      'Save file "worlds/a.vcdbs" (/data/worlds/a.vcdbs) its folder does not exist, so the game server will not start.',
    ]);
  });
});

describe('ServerConfigPathsWarning', () => {
  it('shows nothing when every path is fine', async () => {
    answer(apiCheck());
    renderWarning();

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(screen.queryByTestId('server-config-paths-warning')).not.toBeInTheDocument();
  });

  it('shows the problems and the fix for an Admin key', async () => {
    answer(
      apiCheck({
        mod_paths: [
          { given: 'Mods', resolved: '/data/server/Mods', status: 'ok', problem: false },
          {
            given: '../data/serverdata/Mods',
            resolved: '/data/data/serverdata/Mods',
            status: 'missing',
            problem: true,
          },
        ],
        manager_mods_folder_listed: false,
      })
    );
    renderWarning('admin');

    const warning = await screen.findByTestId('server-config-paths-warning');
    expect(warning).toHaveAttribute('role', 'alert');
    expect(warning).toHaveTextContent('serverconfig.json has path problems');
    expect(warning).toHaveTextContent('Mod folder "../data/serverdata/Mods"');
    expect(warning).toHaveTextContent('ModPaths does not include /data/serverdata/Mods');
    expect(screen.getByTestId('server-config-paths-fix')).toHaveTextContent(
      'Settings → File Manager'
    );
  });

  it('tells a Monitor key to ask an administrator', async () => {
    answer(apiCheck({ manager_mods_folder_listed: false }));
    renderWarning('monitor');

    expect(await screen.findByTestId('server-config-paths-warning')).toHaveTextContent(
      'serverconfig.json has a path problem'
    );
    expect(screen.getByTestId('server-config-paths-fix')).toHaveTextContent(
      'Ask an administrator to correct serverconfig.json.'
    );
  });

  it.each([
    [404, { detail: { code: 'CONFIG_NOT_FOUND', message: 'm' } }],
    [422, { detail: { code: 'CONFIG_FILE_INVALID', message: 'm' } }],
  ])('shows nothing when the check answers %s', async (status, body) => {
    answer(body, false, status);
    renderWarning();

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(screen.queryByTestId('server-config-paths-warning')).not.toBeInTheDocument();
  });

  it('shows nothing for a response of another shape', async () => {
    answer({ status: 'ok', data: { settings: [] } });
    renderWarning();

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(screen.queryByTestId('server-config-paths-warning')).not.toBeInTheDocument();
  });
});
