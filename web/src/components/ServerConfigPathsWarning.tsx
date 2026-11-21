/**
 * ServerConfigPathsWarning - a wrong mod or save path in serverconfig.json (Story 25.2).
 *
 * Shown above the Game Settings groups when the path check (Story 25.1,
 * GET /config/game/paths) finds a problem, or when the folder the manager installs mods
 * into is not in ModPaths (FR348, Epic 25 ADR-3). Each problem names the path as written
 * and as the game resolves it. An Admin key is told how to fix it; the file browser
 * cannot be linked to a file, so the warning names where to go. Renders nothing when
 * there is no problem, while loading, or when the check fails (ADR-3 decision 2).
 */

import { AlertTriangle } from 'lucide-react';
import { useIsAdmin } from '@/api/hooks/use-auth-me';
import type { ServerConfigPathCheck, ServerConfigPathEntry } from '@/api/types';
import { useServerConfigPaths } from '@/hooks/use-game-config';

/** What is wrong with a path, in the admin's words. */
export function pathProblem(entry: ServerConfigPathEntry, kind: 'mod' | 'save'): string {
  switch (entry.status) {
    case 'missing':
      return kind === 'save'
        ? 'its folder does not exist, so the game server will not start'
        : 'does not exist';
    case 'not_a_directory':
      return 'is a file, not a folder';
    case 'not_a_file':
      return 'is a folder, not a file';
    case 'not_readable':
      return 'cannot be read by the game server';
    case 'not_writable':
      return 'cannot be written by the game server';
    case 'invalid':
      return 'is not a usable path';
    default:
      return 'cannot be used';
  }
}

/** True for a response with the path check's shape (anything else shows nothing). */
function isPathCheck(value: unknown): value is ServerConfigPathCheck {
  if (typeof value !== 'object' || value === null) return false;
  const check = value as Partial<ServerConfigPathCheck>;
  return (
    Array.isArray(check.modPaths) &&
    typeof check.saveFile === 'object' &&
    check.saveFile !== null &&
    typeof check.managerModsFolderListed === 'boolean'
  );
}

/** The problem lines, in display order; empty when there is none. */
export function pathProblemLines(check: ServerConfigPathCheck): string[] {
  const lines: string[] = [];
  for (const entry of check.modPaths) {
    if (!entry.problem) continue;
    if (entry.given === null) {
      lines.push('ModPaths is not a list of folder names.');
      continue;
    }
    const where = entry.resolved && entry.resolved !== entry.given ? ` (${entry.resolved})` : '';
    lines.push(`Mod folder "${entry.given}"${where} ${pathProblem(entry, 'mod')}.`);
  }
  if (!check.managerModsFolderListed) {
    const folder = check.managerModsFolder || 'the manager’s mods folder';
    lines.push(
      `ModPaths does not include ${folder}, where the manager installs mods, so the game loads none of them.`
    );
  }
  const save = check.saveFile;
  if (save.problem) {
    const name = save.given ?? save.resolved ?? 'the save file';
    const where = save.resolved && save.resolved !== name ? ` (${save.resolved})` : '';
    lines.push(`Save file "${name}"${where} ${pathProblem(save, 'save')}.`);
  }
  return lines;
}

export function ServerConfigPathsWarning() {
  const { data, isError } = useServerConfigPaths();
  const { isAdmin } = useIsAdmin();
  const check = data?.data;

  if (isError || !isPathCheck(check)) {
    return null;
  }
  const lines = pathProblemLines(check);
  if (lines.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      className="flex gap-3 rounded-lg border border-warning/50 bg-warning/10 p-4 text-sm"
      data-testid="server-config-paths-warning"
    >
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" aria-hidden="true" />
      <div className="min-w-0 space-y-2">
        <p className="font-medium">
          {lines.length === 1
            ? 'serverconfig.json has a path problem'
            : 'serverconfig.json has path problems'}
        </p>
        <ul className="list-disc space-y-1 pl-5 break-words">
          {lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <p className="text-muted-foreground" data-testid="server-config-paths-fix">
          {isAdmin
            ? 'Use absolute paths such as /data/serverdata/Mods. Edit serverconfig.json in Settings → File Manager while the game server is stopped.'
            : 'Ask an administrator to correct serverconfig.json.'}
        </p>
      </div>
    </div>
  );
}
