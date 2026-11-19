/**
 * CodeView: a CodeMirror 6 view or editor for config file text (Story 23.5, ADR-5).
 *
 * Read-only for viewing (Admin's view of a file with its comments) or editable. The
 * extensions are listed one by one (no `basicSetup`), so the bundle stays small. Loaded
 * on demand through `LazyCodeView`, so CodeMirror is in its own chunk.
 */

import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { Compartment, EditorSelection, EditorState } from '@codemirror/state';
import {
  EditorView,
  drawSelection,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
} from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
import { syntaxHighlighting } from '@codemirror/language';
import { highlightSelectionMatches, searchKeymap } from '@codemirror/search';
import { cn } from '@/lib/utils';
import { json5HighlightStyle, json5Language } from './json5-language';

export interface CodeViewProps {
  /** The text; a new value that differs from the document replaces it. */
  value: string;
  /** View only: no editing (default false). */
  readOnly?: boolean;
  /** Wrap long lines. */
  wordWrap?: boolean;
  /** Called with the whole text after each change. */
  onChange?: (text: string) => void;
  /** Accessible name of the text area. */
  ariaLabel: string;
  className?: string;
  'data-testid'?: string;
}

export interface CodeViewHandle {
  /** Move the cursor to a 1-based line and column and scroll it into view. */
  goTo(line: number, column: number): void;
  focus(): void;
}

const theme = EditorView.theme({
  '&': { height: '100%', fontSize: '0.875rem', backgroundColor: 'transparent' },
  '.cm-scroller': { fontFamily: 'var(--font-mono, ui-monospace, monospace)' },
  '.cm-gutters': {
    backgroundColor: 'transparent',
    color: 'var(--muted-foreground)',
    borderRight: '1px solid var(--border)',
  },
  '&.cm-focused': { outline: 'none' },
  '.cm-content': { caretColor: 'var(--foreground)' },
  '.cm-cursor': { borderLeftColor: 'var(--foreground)' },
});

function editableExtensions(readOnly: boolean) {
  return [EditorState.readOnly.of(readOnly), EditorView.editable.of(!readOnly)];
}

const CodeView = forwardRef<CodeViewHandle, CodeViewProps>(function CodeView(
  { value, readOnly = false, wordWrap = false, onChange, ariaLabel, className, ...rest },
  ref
) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  const editable = useRef(new Compartment());
  const wrapping = useRef(new Compartment());

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // One view per mount; later prop changes are dispatched into it
  useEffect(() => {
    if (!host.current) return;
    const created = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          lineNumbers(),
          highlightActiveLineGutter(),
          history(),
          drawSelection(),
          keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap, indentWithTab]),
          highlightSelectionMatches(),
          json5Language,
          syntaxHighlighting(json5HighlightStyle),
          theme,
          editable.current.of(editableExtensions(readOnly)),
          wrapping.current.of(wordWrap ? EditorView.lineWrapping : []),
          EditorView.contentAttributes.of({ 'aria-label': ariaLabel }),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onChangeRef.current?.(update.state.doc.toString());
          }),
        ],
      }),
    });
    view.current = created;
    return () => {
      created.destroy();
      view.current = null;
    };
    // Created once per mount on purpose: value, readOnly and wordWrap changes are
    // dispatched into it by the effects below, so it never loses its undo history
  }, []);

  useEffect(() => {
    const current = view.current;
    if (!current || current.state.doc.toString() === value) return;
    current.dispatch({ changes: { from: 0, to: current.state.doc.length, insert: value } });
  }, [value]);

  useEffect(() => {
    view.current?.dispatch({
      effects: editable.current.reconfigure(editableExtensions(readOnly)),
    });
  }, [readOnly]);

  useEffect(() => {
    view.current?.dispatch({
      effects: wrapping.current.reconfigure(wordWrap ? EditorView.lineWrapping : []),
    });
  }, [wordWrap]);

  useImperativeHandle(ref, () => ({
    goTo(line, column) {
      const current = view.current;
      if (!current) return;
      const doc = current.state.doc;
      const lineInfo = doc.line(Math.min(Math.max(line, 1), doc.lines));
      const position = Math.min(lineInfo.from + Math.max(column, 1) - 1, lineInfo.to);
      current.dispatch({
        selection: EditorSelection.cursor(position),
        scrollIntoView: true,
      });
      current.focus();
    },
    focus() {
      view.current?.focus();
    },
  }));

  return (
    <div
      ref={host}
      className={cn('h-full min-h-0 overflow-hidden', className)}
      data-testid={rest['data-testid']}
    />
  );
});

export default CodeView;
