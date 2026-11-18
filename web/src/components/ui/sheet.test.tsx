/**
 * Sheet Component Tests
 *
 * Story 21.5: the built-in close button is a 44px target (FR277).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from './sheet';

describe('SheetContent', () => {
  function renderOpenSheet(onOpenChange = vi.fn()) {
    render(
      <Sheet open={true} onOpenChange={onOpenChange}>
        <SheetContent>
          <SheetTitle>Title</SheetTitle>
          <SheetDescription>Description</SheetDescription>
        </SheetContent>
      </Sheet>
    );
    return onOpenChange;
  }

  it('renders a close button with a 44px box', () => {
    renderOpenSheet();

    const close = screen.getByRole('button', { name: 'Close' });
    expect(close).toHaveAttribute('data-slot', 'sheet-close');
    expect(close).toHaveClass(
      'size-11',
      'top-0.5',
      'right-0.5',
      'inline-flex',
      'items-center',
      'justify-center'
    );
    expect(close).not.toHaveClass('top-4');
    expect(close).not.toHaveClass('right-4');
  });

  it('closes the sheet when the close button is clicked', async () => {
    const user = userEvent.setup();
    const onOpenChange = renderOpenSheet();

    await user.click(screen.getByRole('button', { name: 'Close' }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
