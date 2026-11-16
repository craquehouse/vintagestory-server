/**
 * Story 17.5 (FR186): a secret setting whose value was withheld shows only whether
 * it is set, with nothing that could hold or reveal a value.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SecretSettingStatus } from './SecretSettingStatus';

describe('SecretSettingStatus', () => {
  it('shows "Set" when the secret is configured', () => {
    render(<SecretSettingStatus settingKey="Password" label="Password" configured />);

    expect(screen.getByTestId('secret-setting-status-Password')).toHaveTextContent(/^Set$/);
  });

  it('shows "Not set" when the secret is not configured', () => {
    render(<SecretSettingStatus settingKey="Password" label="Password" configured={false} />);

    expect(screen.getByTestId('secret-setting-status-Password')).toHaveTextContent(/^Not set$/);
  });

  it('shows the label and the help line', () => {
    render(<SecretSettingStatus settingKey="Password" label="Password" configured />);

    const container = screen.getByTestId('secret-setting-Password');
    expect(container).toHaveTextContent('Password');
    expect(
      screen.getByText('Only an Admin key can see or change this value.')
    ).toBeInTheDocument();
  });

  it('has no input, no password field and no button', () => {
    const { container } = render(
      <SecretSettingStatus settingKey="Password" label="Password" configured />
    );

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(container.querySelector('input')).toBeNull();
    expect(container.querySelector('[type="password"]')).toBeNull();
  });

  it('passes className to the container', () => {
    render(
      <SecretSettingStatus
        settingKey="Password"
        label="Password"
        configured
        className="extra-class"
      />
    );

    expect(screen.getByTestId('secret-setting-Password')).toHaveClass('extra-class');
  });
});
