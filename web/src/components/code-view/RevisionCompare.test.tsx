import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EditorView } from '@codemirror/view';
import RevisionCompare from './RevisionCompare';

const ORIGINAL = '{\n  "a": 1\n}\n';
const CURRENT = '{\n  "a": 2\n}\n';

function views(container: HTMLElement): EditorView[] {
  return Array.from(container.querySelectorAll('.cm-editor')).map((dom) => {
    const view = EditorView.findFromDOM(dom as HTMLElement);
    if (!view) throw new Error('no view');
    return view;
  });
}

describe('RevisionCompare (Story 23.7)', () => {
  it('shows both versions side by side, read-only', () => {
    const { container } = render(
      <RevisionCompare original={ORIGINAL} current={CURRENT} split data-testid="cmp" />
    );

    expect(container.querySelector('.cm-mergeView')).not.toBeNull();
    const [a, b] = views(container);
    expect(a.state.doc.toString()).toBe(ORIGINAL);
    expect(b.state.doc.toString()).toBe(CURRENT);
    expect(a.state.readOnly && b.state.readOnly).toBe(true);
    expect(screen.getByTestId('cmp')).toHaveAttribute('data-split', 'true');
  });

  it('shows one unified view of the current text with the deletions', () => {
    const { container } = render(
      <RevisionCompare original={ORIGINAL} current={CURRENT} split={false} />
    );

    const all = views(container);
    expect(all).toHaveLength(1);
    expect(all[0].state.doc.toString()).toBe(CURRENT);
    expect(container.querySelector('.cm-deletedChunk')).not.toBeNull();
  });

  it('switches between the layouts', () => {
    const { container, rerender } = render(
      <RevisionCompare original={ORIGINAL} current={CURRENT} split />
    );
    expect(views(container)).toHaveLength(2);

    rerender(<RevisionCompare original={ORIGINAL} current={CURRENT} split={false} />);

    expect(views(container)).toHaveLength(1);
  });
});
