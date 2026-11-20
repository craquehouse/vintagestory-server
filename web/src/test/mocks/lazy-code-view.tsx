/**
 * A textarea stand-in for LazyCodeView in component tests (Story 23.5).
 *
 * CodeMirror itself is tested in `components/code-view/CodeView.test.tsx`; flow tests use
 * this stub so they do not depend on CodeMirror's DOM measuring. `goTo` calls are recorded
 * in `codeViewGoToCalls`.
 *
 * Use: `vi.mock('@/components/code-view/LazyCodeView', () => import('@/test/mocks/lazy-code-view'));`
 */

import { forwardRef, useImperativeHandle } from 'react';
import type { CodeViewHandle, CodeViewProps } from '@/components/code-view/CodeView';

export const codeViewGoToCalls: [number, number][] = [];

export const LazyCodeView = forwardRef<CodeViewHandle, CodeViewProps>(function LazyCodeView(
  { value, readOnly = false, wordWrap = false, onChange, ariaLabel, ...rest },
  ref
) {
  useImperativeHandle(ref, () => ({
    goTo(line, column) {
      codeViewGoToCalls.push([line, column]);
    },
    focus() {},
  }));
  return (
    <textarea
      aria-label={ariaLabel}
      value={value}
      readOnly={readOnly}
      data-wrap={wordWrap ? 'true' : 'false'}
      data-testid={rest['data-testid']}
      onChange={(event) => onChange?.(event.target.value)}
    />
  );
});
