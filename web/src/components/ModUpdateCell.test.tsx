import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ModUpdateCell } from './ModUpdateCell';
import type { ModUpdateStatus } from '@/api/types';

function item(overrides: Partial<ModUpdateStatus> = {}): ModUpdateStatus {
  return {
    slug: 'carryon',
    name: 'Carry On',
    installedVersion: '1.14.1',
    status: 'up_to_date',
    offeredVersion: null,
    offeredCompatibility: null,
    offeredPrerelease: null,
    reason: null,
    checkedAt: '2026-11-09T00:00:00Z',
    error: null,
    ...overrides,
  };
}

describe('ModUpdateCell', () => {
  it('shows the offered version with an Update action', () => {
    const onUpdate = vi.fn();
    render(
      <ModUpdateCell
        status={item({
          status: 'update_available',
          offeredVersion: '1.14.3',
          offeredCompatibility: 'compatible',
          offeredPrerelease: false,
        })}
        onUpdate={onUpdate}
      />
    );

    expect(screen.getByText('v1.14.3')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('mod-update-button-carryon'));
    expect(onUpdate).toHaveBeenCalledTimes(1);
  });

  it('marks an offered pre-release', () => {
    render(
      <ModUpdateCell
        status={item({
          status: 'update_available',
          offeredVersion: '2.0.0-rc.2',
          offeredPrerelease: true,
        })}
      />
    );

    expect(screen.getByText('pre-release')).toBeInTheDocument();
    expect(screen.queryByTestId('mod-update-button-carryon')).not.toBeInTheDocument();
  });

  it('shows a spinner and disables the action while updating', () => {
    render(
      <ModUpdateCell
        status={item({ status: 'update_available', offeredVersion: '1.14.3' })}
        onUpdate={vi.fn()}
        isUpdating
      />
    );

    expect(screen.getByTestId('mod-update-button-carryon')).toBeDisabled();
  });

  it('shows Up to date', () => {
    render(<ModUpdateCell status={item()} />);

    expect(screen.getByTestId('mod-update-carryon')).toHaveTextContent('Up to date');
    expect(screen.getByTestId('mod-update-carryon')).not.toHaveAttribute('title');
  });

  it('shows No compatible update with the game version as tooltip', () => {
    render(<ModUpdateCell status={item({ status: 'blocked' })} gameVersion="1.22.7" />);

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent('No compatible update');
    expect(label).toHaveAttribute(
      'title',
      'Newer releases exist, but none is compatible with game version 1.22.7.'
    );
  });

  it.each([
    ['not_checked', 'Not checked yet. Use "Check for updates".'],
    ['not_in_database', 'Not found in the mod database.'],
    ['installed_release_not_listed', 'The installed version is not listed in the mod database.'],
    ['version_unparsable', 'The installed version could not be compared with newer releases.'],
  ] as const)('shows Unknown with the %s reason as tooltip', (reason, text) => {
    render(<ModUpdateCell status={item({ status: 'unknown', reason })} />);

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent('Unknown');
    expect(label).toHaveAttribute('title', text);
  });

  it('adds the last check error to the tooltip', () => {
    render(
      <ModUpdateCell
        status={item({ status: 'unknown', reason: 'not_checked', error: 'mod database unavailable' })}
      />
    );

    expect(screen.getByTestId('mod-update-carryon')).toHaveAttribute(
      'title',
      'Not checked yet. Use "Check for updates". Last check failed: mod database unavailable'
    );
  });

  it('shows a dash when there is no status', () => {
    render(<ModUpdateCell />);

    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
