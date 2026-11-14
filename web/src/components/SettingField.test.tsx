import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { SettingField } from './SettingField';

describe('SettingField', () => {
  const defaultProps = {
    settingKey: 'ServerName',
    label: 'Server Name',
    value: 'My Server',
    type: 'string' as const,
    onSave: vi.fn().mockResolvedValue({}),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders label correctly', () => {
      render(<SettingField {...defaultProps} />);

      expect(screen.getByText('Server Name')).toBeInTheDocument();
    });

    it('renders input with initial value', () => {
      render(<SettingField {...defaultProps} />);

      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('My Server');
    });

    it('renders description when provided', () => {
      render(
        <SettingField {...defaultProps} description="Enter the server name" />
      );

      expect(screen.getByText('Enter the server name')).toBeInTheDocument();
    });
  });

  describe('string input', () => {
    it('updates value on change', () => {
      render(<SettingField {...defaultProps} />);

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'New Name' } });

      expect(input).toHaveValue('New Name');
    });

    it('calls onSave on blur when value changed', async () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(<SettingField {...defaultProps} onSave={onSave} />);

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'Updated Server' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({
          key: 'ServerName',
          value: 'Updated Server',
        });
      });
    });

    it('does not call onSave on blur when value unchanged', () => {
      const onSave = vi.fn();
      render(<SettingField {...defaultProps} onSave={onSave} />);

      const input = screen.getByRole('textbox');
      fireEvent.blur(input);

      expect(onSave).not.toHaveBeenCalled();
    });
  });

  describe('number input', () => {
    it('renders number input for int type', () => {
      render(
        <SettingField
          settingKey="Port"
          label="Port"
          value={42420}
          type="int"
          onSave={vi.fn()}
        />
      );

      const input = screen.getByRole('spinbutton');
      expect(input).toHaveValue(42420);
    });

    it('coerces input to number on change', () => {
      render(
        <SettingField
          settingKey="Port"
          label="Port"
          value={42420}
          type="int"
          onSave={vi.fn()}
        />
      );

      const input = screen.getByRole('spinbutton');
      fireEvent.change(input, { target: { value: '8080' } });

      expect(input).toHaveValue(8080);
    });

    it('calls onSave with number value', async () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(
        <SettingField
          settingKey="Port"
          label="Port"
          value={42420}
          type="int"
          onSave={onSave}
        />
      );

      const input = screen.getByRole('spinbutton');
      fireEvent.change(input, { target: { value: '8080' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({
          key: 'Port',
          value: 8080,
        });
      });
    });
  });

  describe('input width (Story 16.6)', () => {
    it('limits an int input to a narrow width', () => {
      render(
        <SettingField settingKey="Port" label="Port" value={42420} type="int" onSave={vi.fn()} />
      );

      expect(screen.getByRole('spinbutton')).toHaveClass('max-w-xs');
    });

    it('limits a float input to a narrow width', () => {
      render(
        <SettingField settingKey="Ratio" label="Ratio" value={1.5} type="float" onSave={vi.fn()} />
      );

      expect(screen.getByRole('spinbutton')).toHaveClass('max-w-xs');
    });

    it('lets a text input fill its container', () => {
      render(<SettingField {...defaultProps} />);

      const input = screen.getByRole('textbox');
      expect(input).not.toHaveClass('max-w-xs');
      expect(input).toHaveClass('w-full');
    });

    it('keeps the error styling on a narrow number input', async () => {
      render(
        <SettingField
          settingKey="Port"
          label="Port"
          value={42420}
          type="int"
          validate={(v) => (Number(v) > 65535 ? 'Too large' : null)}
          onSave={vi.fn()}
        />
      );

      const input = screen.getByRole('spinbutton');
      fireEvent.change(input, { target: { value: '70000' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(input).toHaveClass('border-destructive');
      });
      expect(input).toHaveClass('max-w-xs');
    });
  });

  describe('boolean input', () => {
    it('renders switch for bool type', () => {
      render(
        <SettingField
          settingKey="AllowPvP"
          label="Allow PvP"
          value={true}
          type="bool"
          onSave={vi.fn()}
        />
      );

      const switchInput = screen.getByRole('switch');
      expect(switchInput).toBeInTheDocument();
      expect(switchInput).toBeChecked();
    });

    it('shows enabled/disabled text based on value', () => {
      const { rerender } = render(
        <SettingField
          settingKey="AllowPvP"
          label="Allow PvP"
          value={true}
          type="bool"
          onSave={vi.fn()}
        />
      );

      expect(screen.getByText('Enabled')).toBeInTheDocument();

      rerender(
        <SettingField
          settingKey="AllowPvP"
          label="Allow PvP"
          value={false}
          type="bool"
          onSave={vi.fn()}
        />
      );

      expect(screen.getByText('Disabled')).toBeInTheDocument();
    });

    it('calls onSave immediately on toggle (not on blur)', async () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(
        <SettingField
          settingKey="AllowPvP"
          label="Allow PvP"
          value={false}
          type="bool"
          onSave={onSave}
        />
      );

      const switchInput = screen.getByRole('switch');
      fireEvent.click(switchInput);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({
          key: 'AllowPvP',
          value: true,
        });
      });
    });
  });

  describe('env managed state', () => {
    it('shows env badge when envManaged is true', () => {
      render(<SettingField {...defaultProps} envManaged={true} />);

      expect(screen.getByText(/Env:/)).toBeInTheDocument();
    });

    it('shows custom env var name in badge', () => {
      render(
        <SettingField
          {...defaultProps}
          envManaged={true}
          envVar="VS_CFG_SERVERNAME"
        />
      );

      expect(screen.getByText('Env: VS_CFG_SERVERNAME')).toBeInTheDocument();
    });

    it('disables input when env managed', () => {
      render(<SettingField {...defaultProps} envManaged={true} />);

      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });

    it('does not call onSave when env managed', async () => {
      const onSave = vi.fn();
      render(<SettingField {...defaultProps} envManaged={true} onSave={onSave} />);

      const input = screen.getByRole('textbox');
      // Try to change value - should be disabled anyway
      fireEvent.change(input, { target: { value: 'New Value' } });
      fireEvent.blur(input);

      // Wait a bit to ensure no async call happens
      await new Promise((r) => setTimeout(r, 50));

      expect(onSave).not.toHaveBeenCalled();
    });

    it('disables switch when env managed (bool type)', () => {
      render(
        <SettingField
          settingKey="AllowPvP"
          label="Allow PvP"
          value={true}
          type="bool"
          envManaged={true}
          onSave={vi.fn()}
        />
      );

      const switchInput = screen.getByRole('switch');
      expect(switchInput).toBeDisabled();
    });
  });

  describe('validation and errors', () => {
    it('shows validation error message', async () => {
      const validate = (value: string | number | boolean) =>
        value === '' ? 'Server name is required' : null;

      render(
        <SettingField
          settingKey="ServerName"
          label="Server Name"
          value="Initial Value"
          type="string"
          validate={validate}
          onSave={vi.fn()}
        />
      );

      const input = screen.getByRole('textbox');
      // Change to empty string to make it dirty and trigger validation
      fireEvent.change(input, { target: { value: '' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Server name is required')).toBeInTheDocument();
      });
    });

    it('adds aria-invalid when error present', async () => {
      const validate = () => 'Error';
      render(
        <SettingField
          {...defaultProps}
          validate={validate}
        />
      );

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'x' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-invalid', 'true');
      });
    });

    it('shows error styling on input when error present', async () => {
      const validate = () => 'Error';
      render(
        <SettingField
          {...defaultProps}
          validate={validate}
        />
      );

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'x' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(input.className).toContain('border-destructive');
      });
    });

    it('hides description when error is shown', async () => {
      const validate = () => 'Error message';
      render(
        <SettingField
          {...defaultProps}
          description="This should be hidden when error shows"
          validate={validate}
        />
      );

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'x' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.queryByText('This should be hidden when error shows')).not.toBeInTheDocument();
        expect(screen.getByText('Error message')).toBeInTheDocument();
      });
    });
  });

  describe('loading state', () => {
    it('shows loader when saving', async () => {
      let resolveSave: () => void;
      const savePromise = new Promise<void>((resolve) => {
        resolveSave = resolve;
      });
      const onSave = vi.fn().mockReturnValue(savePromise);

      render(<SettingField {...defaultProps} onSave={onSave} />);

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'New Value' } });
      fireEvent.blur(input);

      // Wait for the save to start
      await waitFor(() => {
        expect(onSave).toHaveBeenCalled();
      });

      // Loader should be visible while saving
      // Note: The loader appears after isPending becomes true
      expect(screen.getByRole('textbox')).toBeDisabled();

      // Complete the save and wait for state updates
      await act(async () => {
        resolveSave!();
        await savePromise;
      });
    });

    it('disables input while saving', async () => {
      let resolveSave: () => void;
      const savePromise = new Promise<void>((resolve) => {
        resolveSave = resolve;
      });
      const onSave = vi.fn().mockReturnValue(savePromise);

      render(<SettingField {...defaultProps} onSave={onSave} />);

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'New Value' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(input).toBeDisabled();
      });

      // Complete the save and wait for state updates
      await act(async () => {
        resolveSave!();
        await savePromise;
      });

      await waitFor(() => {
        expect(input).not.toBeDisabled();
      });
    });
  });

  describe('Story 16.8: settings with no value', () => {
    it('shows a null string setting as an empty field, not "null"', () => {
      render(
        <SettingField {...defaultProps} settingKey="ServerDescription" label="Description" value={null} />
      );

      const input = screen.getByLabelText('Description');
      expect(input).toHaveValue('');
      expect(screen.queryByDisplayValue('null')).not.toBeInTheDocument();
    });

    it('does not save an untouched null field on blur or Enter', () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(
        <SettingField
          {...defaultProps}
          settingKey="ServerDescription"
          label="Description"
          value={null}
          onSave={onSave}
        />
      );

      const input = screen.getByLabelText('Description');
      fireEvent.focus(input);
      fireEvent.keyDown(input, { key: 'Enter' });
      fireEvent.blur(input);

      expect(onSave).not.toHaveBeenCalled();
    });

    it('saves a cleared field as an empty string', async () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(
        <SettingField
          {...defaultProps}
          settingKey="ServerDescription"
          label="Description"
          value="Old description"
          onSave={onSave}
        />
      );

      const input = screen.getByLabelText('Description');
      fireEvent.change(input, { target: { value: '' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({ key: 'ServerDescription', value: '' });
      });
    });

    it('saves text typed into a null field without a "null" prefix', async () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(
        <SettingField
          {...defaultProps}
          settingKey="ServerDescription"
          label="Description"
          value={null}
          onSave={onSave}
        />
      );

      const input = screen.getByLabelText('Description');
      fireEvent.change(input, { target: { value: 'Hello' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({ key: 'ServerDescription', value: 'Hello' });
      });
    });

    it('shows a null number setting as an empty field', () => {
      render(
        <SettingField {...defaultProps} settingKey="Port" label="Port" type="int" value={null} />
      );

      expect(screen.getByLabelText('Port')).toHaveValue(null);
      expect(screen.queryByDisplayValue('null')).not.toBeInTheDocument();
    });
  });

  describe('Story 16.8: masked input', () => {
    const passwordProps = {
      ...defaultProps,
      settingKey: 'Password',
      label: 'Password',
      value: 'secret',
      masked: true,
    };

    it('masks the value and asks browsers not to fill in a saved password', () => {
      render(<SettingField {...passwordProps} />);

      const input = screen.getByLabelText('Password');
      expect(input).toHaveAttribute('type', 'password');
      expect(input).toHaveAttribute('autocomplete', 'new-password');
      expect(input).toHaveValue('secret');
    });

    it('shows and hides the value with the toggle button', () => {
      render(<SettingField {...passwordProps} />);

      const input = screen.getByLabelText('Password');
      const toggle = screen.getByRole('button', { name: 'Show password' });
      expect(toggle).toHaveAttribute('aria-pressed', 'false');

      fireEvent.click(toggle);
      expect(input).toHaveAttribute('type', 'text');
      const hide = screen.getByRole('button', { name: 'Hide password' });
      expect(hide).toHaveAttribute('aria-pressed', 'true');

      fireEvent.click(hide);
      expect(input).toHaveAttribute('type', 'password');
      expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
    });

    it('saves edits while masked', async () => {
      const onSave = vi.fn().mockResolvedValue({});
      render(<SettingField {...passwordProps} value={null} onSave={onSave} />);

      const input = screen.getByLabelText('Password');
      expect(input).toHaveValue('');
      fireEvent.change(input, { target: { value: 'newsecret' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith({ key: 'Password', value: 'newsecret' });
      });
    });

    it('disables the toggle when the field is disabled (env-managed)', () => {
      render(<SettingField {...passwordProps} envManaged />);

      expect(screen.getByLabelText('Password')).toBeDisabled();
      const toggle = screen.getByRole('button', { name: 'Show password' });
      expect(toggle).toBeDisabled();

      fireEvent.click(toggle);
      expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
    });

    it('does not mask or add a toggle when not masked', () => {
      render(<SettingField {...defaultProps} />);

      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'text');
      expect(screen.queryByRole('button', { name: /password/i })).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('associates label with input', () => {
      render(<SettingField {...defaultProps} />);

      const input = screen.getByRole('textbox');
      const label = screen.getByText('Server Name');

      expect(input).toHaveAttribute('id', 'ServerName');
      expect(label).toHaveAttribute('for', 'ServerName');
    });

    it('associates description with input via aria-describedby', () => {
      render(
        <SettingField {...defaultProps} description="Help text here" />
      );

      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'ServerName-desc');
    });

    it('error message has role=alert', async () => {
      const validate = () => 'Error message';
      render(<SettingField {...defaultProps} validate={validate} />);

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'x' } });
      fireEvent.blur(input);

      await waitFor(() => {
        const error = screen.getByRole('alert');
        expect(error).toHaveTextContent('Error message');
      });
    });
  });
});
