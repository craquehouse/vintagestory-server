import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NoApiKeyScreen } from './NoApiKeyScreen';

describe('NoApiKeyScreen', () => {
  it('names the heading', () => {
    render(<NoApiKeyScreen devServer={false} />);

    expect(
      screen.getByRole('heading', { level: 1, name: 'No API key configured' })
    ).toBeInTheDocument();
  });

  it('says what to set, that the server must restart and who receives the key', () => {
    render(<NoApiKeyScreen devServer={false} />);

    const text = screen.getByTestId('no-api-key-screen').textContent ?? '';
    expect(text).toContain('VS_API_KEY');
    expect(text).toContain('VS_API_KEY_MONITOR');
    expect(text).toContain('VS_API_KEY_ADMIN');
    expect(text).toContain('restart');
    expect(text).toContain('Anyone who can open this page receives that key');
  });

  it('has no field to enter a key and no button', () => {
    render(<NoApiKeyScreen devServer={false} />);

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows the Vite hint only on the dev server', () => {
    const { unmount } = render(<NoApiKeyScreen devServer={true} />);

    const hint = screen.getByTestId('no-api-key-dev-hint');
    expect(hint).toHaveTextContent('VITE_API_KEY');
    expect(hint).toHaveTextContent('web/.env');
    unmount();

    render(<NoApiKeyScreen devServer={false} />);
    expect(screen.queryByTestId('no-api-key-dev-hint')).not.toBeInTheDocument();
  });
});
