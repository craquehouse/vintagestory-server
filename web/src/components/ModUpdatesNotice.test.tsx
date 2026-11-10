import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import userEvent from '@testing-library/user-event';

const mockUpdates: { data?: { data: { updateCount: number } } } = {};
vi.mock('@/hooks/use-mods', () => ({
  useModUpdates: () => mockUpdates,
}));

import { ModUpdatesNotice } from './ModUpdatesNotice';

function renderNotice() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<ModUpdatesNotice />} />
        <Route path="/game-server/mods/installed" element={<div>Installed tab</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ModUpdatesNotice', () => {
  it('shows the count and opens the Installed tab', async () => {
    mockUpdates.data = { data: { updateCount: 2 } };
    renderNotice();

    const notice = screen.getByTestId('mod-updates-notice');
    expect(notice).toHaveTextContent('2 mod updates available');
    await userEvent.click(notice);
    expect(screen.getByText('Installed tab')).toBeInTheDocument();
  });

  it('uses the singular for one update', () => {
    mockUpdates.data = { data: { updateCount: 1 } };
    renderNotice();

    expect(screen.getByTestId('mod-updates-notice')).toHaveTextContent('1 mod update available');
  });

  it('renders nothing without updates', () => {
    mockUpdates.data = { data: { updateCount: 0 } };
    renderNotice();

    expect(screen.queryByTestId('mod-updates-notice')).not.toBeInTheDocument();
  });

  it('renders nothing before the status loads', () => {
    mockUpdates.data = undefined;
    renderNotice();

    expect(screen.queryByTestId('mod-updates-notice')).not.toBeInTheDocument();
  });
});
