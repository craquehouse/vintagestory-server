import { describe, it, expect, vi } from 'vitest';
import { createRef } from 'react';
import { render, screen } from '@testing-library/react';
import { EditorView } from '@codemirror/view';
import CodeView, { type CodeViewHandle } from './CodeView';

/** The EditorView inside a rendered CodeView. */
function editorOf(container: HTMLElement): EditorView {
  const dom = container.querySelector('.cm-editor');
  if (!(dom instanceof HTMLElement)) throw new Error('no editor');
  const view = EditorView.findFromDOM(dom);
  if (!view) throw new Error('no view');
  return view;
}

describe('CodeView (Story 23.5)', () => {
  it('shows the text with its comments', () => {
    const { container } = render(
      <CodeView value={'{\n  // note\n  "a": 1\n}'} ariaLabel="File text" data-testid="cv" />
    );

    expect(screen.getByTestId('cv')).toBeInTheDocument();
    expect(editorOf(container).state.doc.toString()).toBe('{\n  // note\n  "a": 1\n}');
    expect(container.querySelector('.cm-content')).toHaveAttribute('aria-label', 'File text');
  });

  it('calls onChange with the whole text after a change', () => {
    const onChange = vi.fn();
    const { container } = render(<CodeView value="{}" ariaLabel="t" onChange={onChange} />);
    const view = editorOf(container);

    view.dispatch({ changes: { from: 1, insert: '"a": 1' } });

    expect(onChange).toHaveBeenLastCalledWith('{"a": 1}');
  });

  it('is read-only when asked', () => {
    const { container } = render(<CodeView value="{}" ariaLabel="t" readOnly />);

    expect(editorOf(container).state.readOnly).toBe(true);
    expect(container.querySelector('.cm-content')).toHaveAttribute('contenteditable', 'false');
  });

  it('replaces the document when the value changes', () => {
    const { container, rerender } = render(<CodeView value="{}" ariaLabel="t" />);

    rerender(<CodeView value='{"b": 2}' ariaLabel="t" />);

    expect(editorOf(container).state.doc.toString()).toBe('{"b": 2}');
  });

  it('wraps lines when asked', () => {
    const { container, rerender } = render(<CodeView value="{}" ariaLabel="t" />);
    expect(container.querySelector('.cm-lineWrapping')).toBeNull();

    rerender(<CodeView value="{}" ariaLabel="t" wordWrap />);

    expect(container.querySelector('.cm-lineWrapping')).not.toBeNull();
  });

  it('moves the cursor to a line and column', () => {
    const ref = createRef<CodeViewHandle>();
    const { container } = render(<CodeView ref={ref} value={'{\n  "a": 1\n}'} ariaLabel="t" />);

    ref.current?.goTo(2, 3);

    const view = editorOf(container);
    expect(view.state.selection.main.head).toBe(view.state.doc.line(2).from + 2);
  });
});
