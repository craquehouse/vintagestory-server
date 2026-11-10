import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VersionChangeConfirmDialog } from './VersionChangeConfirmDialog';
import type { VersionChangeConfirmation } from '@/hooks/use-version-change-flow';

const base: VersionChangeConfirmation = {
  slug: 'carryon',
  name: 'Carry On',
  version: '1.14.0',
  installedVersion: '1.14.1',
  kind: 'switch',
  reasons: [],
};

function renderDialog(
  confirmation: VersionChangeConfirmation | null,
  gameVersion: string | null = '1.22.7'
) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <VersionChangeConfirmDialog
      confirmation={confirmation}
      gameVersion={gameVersion}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
  return { onConfirm, onCancel };
}

describe('VersionChangeConfirmDialog', () => {
  it('is closed without a confirmation', () => {
    renderDialog(null);

    expect(screen.queryByTestId('version-change-dialog')).not.toBeInTheDocument();
  });

  it('titles a switch and offers Switch anyway', () => {
    renderDialog({ ...base, reasons: ['older'] });

    expect(screen.getByText('Switch Carry On to v1.14.0?')).toBeInTheDocument();
    expect(screen.getByTestId('version-change-confirm')).toHaveTextContent('Switch anyway');
  });

  it('titles an update and offers Update anyway', () => {
    renderDialog({ ...base, kind: 'update', version: '1.15.0', reasons: ['not_verified'] });

    expect(screen.getByText('Update Carry On to v1.15.0?')).toBeInTheDocument();
    expect(screen.getByTestId('version-change-confirm')).toHaveTextContent('Update anyway');
  });

  it.each([
    ['not_verified', 'Not verified for game version 1.22.7. It may still work.'],
    ['incompatible', 'Not tagged for game version 1.22.7. It may not load.'],
    ['prerelease', 'v1.14.0 is a pre-release; the installed version is a stable release.'],
    [
      'older',
      'v1.14.0 is older than the installed v1.14.1. Worlds saved with a newer version may not load correctly.',
    ],
  ] as const)('explains the %s reason', (reason, text) => {
    renderDialog({ ...base, reasons: [reason] });

    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it('lists every reason', () => {
    renderDialog({ ...base, reasons: ['older', 'incompatible'] });

    expect(screen.getByTestId('version-change-reasons').querySelectorAll('li')).toHaveLength(2);
  });

  it('falls back when the game version is unknown', () => {
    renderDialog({ ...base, reasons: ['incompatible'] }, null);

    expect(
      screen.getByText('Not tagged for the installed game version. It may not load.')
    ).toBeInTheDocument();
  });

  it('shows a generic line when no reason is recognized', () => {
    renderDialog(base);

    expect(screen.getByText('This change needs confirmation.')).toBeInTheDocument();
  });

  it('confirms and cancels', () => {
    const { onConfirm, onCancel } = renderDialog({ ...base, reasons: ['older'] });

    fireEvent.click(screen.getByTestId('version-change-confirm'));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('version-change-cancel'));
    expect(onCancel).toHaveBeenCalled();
  });
});
