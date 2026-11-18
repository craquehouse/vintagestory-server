/**
 * NewTabLink - a link that opens in a new tab and tells a screen reader so (Story 21.6,
 * VSS-woae, Epic 21 ADR-10 decision 1).
 *
 * Sets `target="_blank"` and `rel="noopener noreferrer"` and ends the link with a visually
 * hidden `OPENS_IN_NEW_TAB` note, after a space so the name reads "Docs (opens in a new tab)".
 * `aria-label` is not accepted: it would replace the content, note included, as the name.
 */

import type { ComponentProps } from 'react';
import { OPENS_IN_NEW_TAB } from '@/lib/new-tab';

type NewTabLinkProps = Omit<ComponentProps<'a'>, 'target' | 'rel' | 'aria-label'>;

export function NewTabLink({ children, ...props }: NewTabLinkProps) {
  return (
    <a {...props} target="_blank" rel="noopener noreferrer">
      {children} <span className="sr-only">{OPENS_IN_NEW_TAB}</span>
    </a>
  );
}
