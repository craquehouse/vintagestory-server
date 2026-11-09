import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router';
import { PageErrorBoundary } from './PageErrorBoundary';

function BrokenPage(): never {
  throw new Error('page failed');
}

function renderAt(path: string, onReload = vi.fn()) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Link to="/working">Go to working page</Link>
      <PageErrorBoundary onReload={onReload}>
        <Routes>
          <Route path="/broken" element={<BrokenPage />} />
          <Route path="/working" element={<p>Working page</p>} />
        </Routes>
      </PageErrorBoundary>
    </MemoryRouter>,
  );
  return onReload;
}

describe('PageErrorBoundary', () => {
  beforeEach(() => {
    // React logs every error caught by a boundary.
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the page when nothing fails', () => {
    renderAt('/working');

    expect(screen.getByText('Working page')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a message instead of the failed page', () => {
    renderAt('/broken');

    expect(screen.getByRole('alert')).toHaveTextContent("This page couldn't be loaded");
  });

  it('keeps content outside the boundary on screen', () => {
    renderAt('/broken');

    expect(screen.getByRole('link', { name: 'Go to working page' })).toBeInTheDocument();
  });

  it('reloads when the button is clicked', async () => {
    const onReload = renderAt('/broken');

    await userEvent.click(screen.getByRole('button', { name: 'Reload' }));

    expect(onReload).toHaveBeenCalledTimes(1);
  });

  it('recovers when navigating to another page', async () => {
    renderAt('/broken');

    await userEvent.click(screen.getByRole('link', { name: 'Go to working page' }));

    expect(await screen.findByText('Working page')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
