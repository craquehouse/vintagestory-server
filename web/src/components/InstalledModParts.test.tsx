import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  ModCompatibility,
  ModEnableToggle,
  ModNameLink,
  ModRemoveButton,
} from './InstalledModParts';
import type { ModCompatibility as ModCompatibilityInfo, ModInfo } from '@/api/types';

function mod(overrides: Partial<ModInfo> = {}): ModInfo {
  return {
    filename: 'playercorpse-1.11.1.zip',
    slug: 'playercorpse',
    version: '1.11.1',
    enabled: true,
    installedAt: '2026-11-13T00:00:00Z',
    assetId: 1234,
    name: 'Player Corpse',
    authors: [],
    description: null,
    side: 'Both',
    ...overrides,
  };
}

function compatibility(overrides: Partial<ModCompatibilityInfo> = {}): ModCompatibilityInfo {
  return {
    status: 'incompatible',
    gameVersion: '1.22.7',
    modVersion: '1.11.1',
    message: 'Last supported game version: 1.21.1.',
    latestSupportedGameVersion: '1.21.1',
    ...overrides,
  };
}

describe('InstalledModParts (Story 16.5)', () => {
  describe('ModNameLink', () => {
    it('links to the mod database page by asset ID and shows the slug under the name', () => {
      render(<ModNameLink mod={mod()} />);
      const link = screen.getByTestId('mod-link-playercorpse');
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/show/mod/1234');
      expect(link).toHaveTextContent('Player Corpse');
      expect(screen.getByText('playercorpse')).toBeInTheDocument();
    });

    it('falls back to the slug URL and shows only the slug without a name', () => {
      render(<ModNameLink mod={mod({ assetId: 0, name: null })} />);
      const link = screen.getByTestId('mod-link-playercorpse');
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/playercorpse');
      expect(screen.getAllByText('playercorpse')).toHaveLength(1);
    });
  });

  describe('ModCompatibility', () => {
    it('shows the badge with the message as tooltip and the latest supported version', () => {
      render(
        <ModCompatibility slug="playercorpse" status="incompatible" compatibility={compatibility()} />
      );
      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toHaveAttribute('data-status', 'incompatible');
      expect(badge).toHaveAttribute('title', 'Last supported game version: 1.21.1.');
      expect(screen.getByTestId('mod-latest-supported-playercorpse')).toHaveTextContent(
        'Supports up to 1.21.1'
      );
      expect(screen.queryByTestId('mod-compatibility-message-playercorpse')).not.toBeInTheDocument();
    });

    it.each(['incompatible', 'not_verified'] as const)(
      'shows the message as text for %s with showMessage',
      (status) => {
        render(
          <ModCompatibility
            slug="playercorpse"
            status={status}
            compatibility={compatibility({ status })}
            showMessage
          />
        );
        expect(screen.getByTestId('mod-compatibility-message-playercorpse')).toHaveTextContent(
          'Last supported game version: 1.21.1.'
        );
      }
    );

    it('shows neither the version nor the message for a compatible mod', () => {
      render(
        <ModCompatibility
          slug="playercorpse"
          status="compatible"
          compatibility={compatibility({ status: 'compatible', message: 'Compatible.' })}
          showMessage
        />
      );
      expect(screen.queryByTestId('mod-latest-supported-playercorpse')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-compatibility-message-playercorpse')).not.toBeInTheDocument();
    });

    it('shows only the badge while compatibility details are unknown', () => {
      render(<ModCompatibility slug="playercorpse" status="not_verified" showMessage />);
      expect(screen.getByTestId('compatibility-badge')).toHaveAttribute('data-status', 'not_verified');
      expect(screen.queryByTestId('mod-latest-supported-playercorpse')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-compatibility-message-playercorpse')).not.toBeInTheDocument();
    });
  });

  describe('ModEnableToggle', () => {
    it('reflects the enabled state and calls onToggle', () => {
      const onToggle = vi.fn();
      render(<ModEnableToggle mod={mod()} isToggling={false} onToggle={onToggle} />);
      const toggle = screen.getByRole('switch', { name: 'Disable mod' });
      expect(toggle).toBeChecked();
      fireEvent.click(toggle);
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('is disabled with a spinner while toggling', () => {
      render(<ModEnableToggle mod={mod({ enabled: false })} isToggling onToggle={vi.fn()} />);
      expect(screen.getByRole('switch', { name: 'Enable mod' })).toBeDisabled();
      expect(screen.getByTestId('mod-toggle-spinner-playercorpse')).toBeInTheDocument();
    });
  });

  describe('ModRemoveButton', () => {
    it('is named after the mod and calls onRemove', () => {
      const onRemove = vi.fn();
      render(<ModRemoveButton mod={mod()} onRemove={onRemove} />);
      fireEvent.click(screen.getByRole('button', { name: 'Remove Player Corpse' }));
      expect(onRemove).toHaveBeenCalledTimes(1);
    });

    it('accepts extra classes for its size', () => {
      render(<ModRemoveButton mod={mod({ name: null })} onRemove={vi.fn()} className="size-11" />);
      expect(screen.getByRole('button', { name: 'Remove playercorpse' })).toHaveClass('size-11');
    });
  });
});
