/**
 * Shared mock for useGameSetting hook.
 *
 * Usage in test files:
 * ```typescript
 * import { mockUseGameSetting } from '@/test/mocks/use-game-config';
 *
 * vi.mock('@/hooks/use-game-config', () => ({
 *   useGameSetting: (key: string) => mockUseGameSetting(key),
 * }));
 *
 * beforeEach(() => {
 *   mockUseGameSetting.mockReturnValue(undefined);
 * });
 * ```
 */
export const mockUseGameSetting = vi.fn();
