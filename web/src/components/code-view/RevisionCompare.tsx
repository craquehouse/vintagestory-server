/**
 * RevisionCompare: an earlier version of a config file compared with its current text
 * (Story 23.7, Epic 23 ADR-8 decision 2).
 *
 * CodeMirror's merge view, read-only: side by side (the earlier version left, the current
 * text right) when `split`, else one view of the current text with the earlier lines shown
 * as deletions. Loaded on demand with the rest of CodeMirror (`LazyRevisionCompare`).
 */

import { useEffect, useRef } from 'react';
import { EditorState, type Extension } from '@codemirror/state';
import { EditorView, lineNumbers } from '@codemirror/view';
import { syntaxHighlighting } from '@codemirror/language';
import { MergeView, unifiedMergeView } from '@codemirror/merge';
import { cn } from '@/lib/utils';
import { json5HighlightStyle, json5Language } from './json5-language';

export interface RevisionCompareProps {
  /** The earlier version's text. */
  original: string;
  /** The file's current text. */
  current: string;
  /** Side by side (wide screens) or unified (narrow ones). */
  split: boolean;
  wordWrap?: boolean;
  className?: string;
  'data-testid'?: string;
}

function readOnly(wordWrap: boolean): Extension[] {
  return [
    lineNumbers(),
    json5Language,
    syntaxHighlighting(json5HighlightStyle),
    EditorState.readOnly.of(true),
    EditorView.editable.of(false),
    wordWrap ? EditorView.lineWrapping : [],
    EditorView.theme({
      '&': { fontSize: '0.875rem', backgroundColor: 'transparent' },
      '.cm-scroller': { fontFamily: 'var(--font-mono, ui-monospace, monospace)' },
      '.cm-gutters': {
        backgroundColor: 'transparent',
        color: 'var(--muted-foreground)',
        borderRight: '1px solid var(--border)',
      },
    }),
  ];
}

export default function RevisionCompare({
  original,
  current,
  split,
  wordWrap = false,
  className,
  ...rest
}: RevisionCompareProps) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const parent = host.current;
    if (!parent) return;
    if (split) {
      const view = new MergeView({
        a: { doc: original, extensions: readOnly(wordWrap) },
        b: { doc: current, extensions: readOnly(wordWrap) },
        parent,
        gutter: true,
      });
      return () => view.destroy();
    }
    const view = new EditorView({
      parent,
      state: EditorState.create({
        doc: current,
        extensions: [
          ...readOnly(wordWrap),
          unifiedMergeView({ original, mergeControls: false, gutter: true }),
        ],
      }),
    });
    return () => view.destroy();
  }, [original, current, split, wordWrap]);

  return (
    <div
      ref={host}
      className={cn('h-full overflow-auto', className)}
      data-split={split ? 'true' : 'false'}
      data-testid={rest['data-testid']}
    />
  );
}
