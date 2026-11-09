/**
 * Error boundary for route pages.
 *
 * Keeps the layout and navigation on screen when a page fails to load or render,
 * for example when its chunk can't be fetched.
 */

import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useLocation } from 'react-router';
import { Button } from '@/components/ui/button';

interface BoundaryProps {
  children: ReactNode;
  /** Clears the error when it changes, so navigating away recovers. */
  resetKey: string;
  onReload: () => void;
}

interface BoundaryState {
  hasError: boolean;
}

class Boundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { hasError: false };

  static getDerivedStateFromError(): BoundaryState {
    return { hasError: true };
  }

  componentDidUpdate(previous: BoundaryProps): void {
    if (this.state.hasError && previous.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false });
    }
  }

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex flex-col items-start gap-3 p-4" role="alert" data-testid="page-error">
        <div className="flex items-center gap-2">
          <AlertTriangle className="size-5 text-destructive" aria-hidden="true" />
          <h1 className="text-lg font-semibold">This page couldn't be loaded</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Reloading usually fixes this. If it keeps happening, the server may be updating.
        </p>
        <Button onClick={this.props.onReload}>Reload</Button>
      </div>
    );
  }
}

interface PageErrorBoundaryProps {
  children: ReactNode;
  onReload?: () => void;
}

export function PageErrorBoundary({
  children,
  onReload = () => window.location.reload(),
}: PageErrorBoundaryProps) {
  const { pathname } = useLocation();

  return (
    <Boundary resetKey={pathname} onReload={onReload}>
      {children}
    </Boundary>
  );
}
