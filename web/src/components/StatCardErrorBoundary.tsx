/**
 * Error boundary for StatCard components.
 *
 * Story 12.4: Dashboard Stats Cards (Review Follow-up)
 *
 * Provides graceful error handling for individual stat cards,
 * preventing one failing card from breaking the entire dashboard.
 */

import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface StatCardErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode;
  /** Card title to display in error state */
  title: string;
  /** Test ID for the error state */
  testId?: string;
}

interface StatCardErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary that catches errors in stat card components.
 *
 * Renders a fallback card with error message instead of crashing.
 * This ensures one failing card doesn't break the entire dashboard.
 */
export class StatCardErrorBoundary extends Component<
  StatCardErrorBoundaryProps,
  StatCardErrorBoundaryState
> {
  constructor(props: StatCardErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): StatCardErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log error for debugging (could integrate with error reporting service)
    console.error('StatCard error:', error, errorInfo);
  }

  render(): ReactNode {
    const { hasError } = this.state;
    const { children, title, testId } = this.props;

    if (hasError) {
      return (
        <Card
          className="min-h-[140px] border-destructive/50"
          data-testid={testId ? `${testId}-error` : undefined}
          role="region"
          aria-label={`${title} - Error`}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <AlertTriangle
                className="size-5 text-destructive"
                aria-hidden="true"
              />
              <CardTitle className="text-base font-medium">{title}</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">
              Unable to load card data
            </div>
          </CardContent>
        </Card>
      );
    }

    return children;
  }
}
