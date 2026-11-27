import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InstalledModCard } from './InstalledModCard';
import type { ModTableRow } from './InstalledModParts';
import type { ModUpdateStatus } from '@/api/types';

function updateStatus(overrides: Partial<ModUpdateStatus>): ModUpdateStatus {
  return {
    slug: 'playercorpse',
    name: 'Player Corpse',
    installedVersion: '1.11.1',
    status: 'unknown',
    reason: null,
    offeredVersion: null,
    offeredCompatibility: null,
    offeredPrerelease: null,
    checkedAt: '2026-11-19T00:00:00Z',
    error: null,
    ...overrides,
  };
}

function row(overrides: Partial<ModTableRow> = {}): ModTableRow {
  return {
    filename: 'playercorpse-1.11.1.zip',
    slug: 'playercorpse',
    version: '1.11.1',
    enabled: true,
    installedAt: '2026-11-13T00:00:00Z',
    assetId: 0,
    name: 'Player Corpse',
    authors: [],
    description: null,
    side: 'Both',
    source: 'folder',
    sourceUrl: null,
    compatibilityStatus: 'not_verified',
    ...overrides,
  };
}

function renderCard(mod: ModTableRow) {
  render(
    <ul>
      <InstalledModCard
        mod={mod}
        gameVersion="1.22.7"
        isToggling={false}
        isUpdating={false}
        onToggle={vi.fn()}
        onUpdate={vi.fn()}
        onRemove={vi.fn()}
      />
    </ul>
  );
}

describe('InstalledModCard local mods (Story 24.4, FR335)', () => {
  it('shows a mod the mod database does not know as a local mod, without a link', () => {
    renderCard(row({ updateStatus: updateStatus({ reason: 'not_in_database' }) }));

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByTestId('mod-name-playercorpse')).toHaveTextContent('Player Corpse');
    expect(screen.getByTestId('mod-update-playercorpse')).toHaveTextContent(/^Local mod/);
  });

  it('keeps the link for a mod not checked yet', () => {
    renderCard(row({ updateStatus: updateStatus({ reason: 'not_checked' }) }));

    expect(screen.getByTestId('mod-link-playercorpse')).toHaveAttribute(
      'href',
      'https://mods.vintagestory.at/playercorpse'
    );
  });

  // Story 28.1 (FR355)
  it('shows an uploaded mod without a mod database link, with its source', () => {
    renderCard(
      row({
        source: 'upload',
        compatibility: {
          status: 'not_verified',
          gameVersion: null,
          modVersion: '1.11.1',
          message: 'Not from the mod database',
          latestSupportedGameVersion: null,
        },
        updateStatus: updateStatus({ reason: 'manual_install' }),
      })
    );

    expect(screen.queryByTestId('mod-link-playercorpse')).not.toBeInTheDocument();
    expect(screen.getByTestId('mod-name-playercorpse')).toHaveTextContent('Player Corpse');
    expect(screen.getByTestId('mod-update-playercorpse')).toHaveTextContent(/^Uploaded file/);
    expect(screen.getByText('Not from the mod database')).toBeInTheDocument();
  });

  it('shows a linked mod as installed from a link on the card', () => {
    renderCard(
      row({
        source: 'url',
        sourceUrl: 'https://github.com/me/playercorpse/releases/download/v1/pc.zip',
        updateStatus: updateStatus({ reason: 'manual_install' }),
      })
    );

    expect(screen.queryByTestId('mod-link-playercorpse')).not.toBeInTheDocument();
    expect(screen.getByTestId('mod-update-playercorpse')).toHaveTextContent(
      /^Installed from a link/
    );
  });
});
