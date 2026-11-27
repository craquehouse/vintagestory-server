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
    ['installed_release_not_listed', 'The installed version is not listed in the mod database.'],
    ['version_unparsable', 'The installed version could not be compared with newer releases.'],
  ] as const)('shows Unknown with the %s reason as tooltip', (reason, text) => {
    render(<ModUpdateCell status={item({ status: 'unknown', reason })} />);

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent('Unknown');
    expect(label).not.toHaveTextContent(/^Not checked yet/);
    expect(label).toHaveAttribute('title', text);
  });

  // Story 28.1 (FR355, Epic 28 ADR-2 decision 3)
  it('shows an uploaded mod as an uploaded file', () => {
    render(
      <ModUpdateCell
        status={item({ status: 'unknown', reason: 'manual_install' })}
        source="upload"
        onUpdate={vi.fn()}
      />
    );

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent(/^Uploaded file/);
    expect(label).toHaveAttribute(
      'title',
      'Uploaded file; not from the mod database, so it gets no update offers.'
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows a linked mod as installed from a link, naming the host', () => {
    render(
      <ModUpdateCell
        status={item({ status: 'unknown', reason: 'manual_install' })}
        source="url"
        sourceUrl="https://github.com/me/mod/releases/download/v1/mod.zip"
      />
    );

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent(/^Installed from a link/);
    expect(label).toHaveAttribute(
      'title',
      'Installed from github.com; not from the mod database, so it gets no update offers.'
    );
  });

  it('says "a link" when the stored link does not parse', () => {
    render(
      <ModUpdateCell
        status={item({ status: 'unknown', reason: 'manual_install' })}
        source="url"
        sourceUrl="not a url"
      />
    );

    expect(screen.getByTestId('mod-update-carryon')).toHaveAttribute(
      'title',
      'Installed from a link; not from the mod database, so it gets no update offers.'
    );
  });

  // Story 24.4 (FR335, Epic 24 ADR-1 decision 4)
  it('shows a mod the mod database does not know as a local mod', () => {
    render(<ModUpdateCell status={item({ status: 'unknown', reason: 'not_in_database' })} />);

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent(/^Local mod/);
    expect(label).not.toHaveTextContent('Unknown');
    expect(label).toHaveAttribute(
      'title',
      'Not in the mod database: it has no mod database page and gets no update offers.'
    );
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows Unknown when no reason is given', () => {
    render(<ModUpdateCell status={item({ status: 'unknown' })} />);

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent('Unknown');
    expect(label).toHaveAttribute('title', 'Update status is unknown.');
  });

  it('shows Not checked yet for a mod without update data (Story 17.4)', () => {
    render(<ModUpdateCell status={item({ status: 'unknown', reason: 'not_checked' })} />);

    const label = screen.getByTestId('mod-update-carryon');
    expect(label).toHaveTextContent(/^Not checked yet/);
    expect(label).not.toHaveTextContent('Unknown');
    expect(label).toHaveAttribute('title', 'Use "Check for updates" to look it up now.');
  });

  it('adds the last check error to the tooltip', () => {
    render(
      <ModUpdateCell
        status={item({
          status: 'unknown',
          reason: 'not_checked',
          error: 'mod database unavailable',
        })}
      />
    );

    expect(screen.getByTestId('mod-update-carryon')).toHaveAttribute(
      'title',
      'Use "Check for updates" to look it up now. Last check failed: mod database unavailable'
    );
  });

  it('shows a dash when there is no status', () => {
    render(<ModUpdateCell />);

    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('gives screen readers the reason as text, not only as a tooltip', () => {
    render(<ModUpdateCell status={item({ status: 'unknown', reason: 'not_in_database' })} />);

    const reason = screen.getByText(
      'Not in the mod database: it has no mod database page and gets no update offers.'
    );
    expect(reason).toHaveClass('sr-only');
    expect(screen.getByTestId('mod-update-carryon')).toContainElement(reason);
  });

  it('passes extra classes to the Update button (Story 16.5 card touch size)', () => {
    render(
      <ModUpdateCell
        status={item({
          status: 'update_available',
          offeredVersion: '1.14.3',
          offeredCompatibility: 'compatible',
          offeredPrerelease: false,
        })}
        onUpdate={vi.fn()}
        buttonClassName="min-h-11"
      />
    );

    expect(screen.getByTestId('mod-update-button-carryon')).toHaveClass('min-h-11');
  });

  it('lets the Update button wrap under the offered version (Story 18.4)', () => {
    render(
      <ModUpdateCell
        status={item({
          status: 'update_available',
          offeredVersion: '1.15.0-rc.1',
          offeredCompatibility: 'compatible',
          offeredPrerelease: true,
        })}
        onUpdate={vi.fn()}
      />
    );

    expect(screen.getByTestId('mod-update-carryon')).toHaveClass('flex', 'flex-wrap');
  });
});
