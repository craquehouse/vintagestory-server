/**
 * A stand-in for LazyRevisionCompare in component tests (Story 23.7); CodeMirror's merge
 * view itself is tested in `components/code-view/RevisionCompare.test.tsx`.
 *
 * Use: `vi.mock('@/components/code-view/LazyRevisionCompare', () => import('@/test/mocks/lazy-revision-compare'));`
 */

import type { RevisionCompareProps } from '@/components/code-view/RevisionCompare';

export function LazyRevisionCompare({ original, current, split, ...rest }: RevisionCompareProps) {
  return (
    <div data-testid={rest['data-testid']} data-split={split ? 'true' : 'false'}>
      <pre data-testid="compare-original">{original}</pre>
      <pre data-testid="compare-current">{current}</pre>
    </div>
  );
}
