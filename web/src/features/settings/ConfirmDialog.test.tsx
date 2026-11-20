import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmDialog } from './ConfirmDialog';

function setup() {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ConfirmDialog
      open
      title="Discard?"
      description="Discard your changes?"
      confirmLabel="Discard"
      cancelLabel="Keep editing"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
  return { onConfirm, onCancel };
}

describe('ConfirmDialog (Story 23.5 review L-5)', () => {
  it('calls onConfirm once and not onCancel', () => {
    const { onConfirm, onCancel } = setup();

    fireEvent.click(screen.getByRole('button', { name: 'Discard' }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('calls onCancel once from the cancel button', () => {
    const { onConfirm, onCancel } = setup();

    fireEvent.click(screen.getByRole('button', { name: 'Keep editing' }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('calls onCancel once on Escape', () => {
    const { onCancel } = setup();

    fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Escape' });

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
