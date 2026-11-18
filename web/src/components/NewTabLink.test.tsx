import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ExternalLink } from 'lucide-react';
import { NewTabLink } from './NewTabLink';

describe('NewTabLink (Story 21.6, VSS-woae)', () => {
  it('opens in a new tab without an opener or referrer', () => {
    render(<NewTabLink href="https://example.com/docs">Docs</NewTabLink>);
    const link = screen.getByRole('link', { name: 'Docs (opens in a new tab)' });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('passes href, className and data-testid through', () => {
    render(
      <NewTabLink href="https://example.com/docs" className="text-sm" data-testid="docs-link">
        Docs
      </NewTabLink>
    );
    const link = screen.getByTestId('docs-link');
    expect(link).toHaveAttribute('href', 'https://example.com/docs');
    expect(link).toHaveClass('text-sm');
  });

  it('keeps its children before the hidden note', () => {
    render(
      <NewTabLink href="https://example.com">
        <ExternalLink aria-hidden="true" data-testid="docs-icon" />
        Docs
      </NewTabLink>
    );
    const link = screen.getByRole('link', { name: 'Docs (opens in a new tab)' });
    expect(link.firstElementChild).toBe(screen.getByTestId('docs-icon'));
    const note = link.lastElementChild;
    expect(note).toHaveClass('sr-only');
    expect(note).toHaveTextContent('(opens in a new tab)');
  });
});
