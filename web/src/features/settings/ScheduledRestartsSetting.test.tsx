import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { ApiError } from '@/api/errors';
import { ScheduledRestartsSetting } from './ScheduledRestartsSetting';

/**
 * Story 22.6: the Scheduled Restarts editor. No fetch: `onSave` is a mock, and a small
 * parent echoes each saved list back as `times`, as the panel's query does.
 */

type SaveParams = { key: string; value: string[] };
type OnSave = (params: SaveParams) => Promise<unknown>;

const GAP_MESSAGE =
  "'04:00' and '04:10' are 10 minutes apart; restart times must be at least 16 minutes apart";
const SERVER_MESSAGE = `Invalid value for 'scheduled_restart_times': ${GAP_MESSAGE}`;

function EchoParent({ initial, onSave }: { initial: string[]; onSave: OnSave }) {
  const [times, setTimes] = useState(initial);
  return (
    <ScheduledRestartsSetting
      times={times}
      onSave={async (params) => {
        const result = await onSave(params);
        setTimes(params.value);
        return result;
      }}
    />
  );
}

function renderEcho(initial: string[] = [], onSave: OnSave = vi.fn().mockResolvedValue(undefined)) {
  render(<EchoParent initial={initial} onSave={onSave} />);
  return onSave;
}

/** A save that waits until the test resolves or rejects it. */
function deferredSave() {
  const resolvers: Array<{ resolve: () => void; reject: (err: Error) => void }> = [];
  const onSave = vi.fn().mockImplementation(
    () =>
      new Promise<void>((resolve, reject) => {
        resolvers.push({ resolve, reject });
      })
  );
  return { onSave, resolvers };
}

function timeInput(n: number): HTMLInputElement {
  const input = screen.getByLabelText(`Restart time ${n}`);
  if (!(input instanceof HTMLInputElement)) throw new Error(`Restart time ${n} is not an input`);
  return input;
}

function addButton(): HTMLElement {
  return screen.getByTestId('add-restart-time');
}

function shownTimes(): string[] {
  return screen.queryAllByLabelText(/^Restart time \d+$/).map((el) => {
    if (!(el instanceof HTMLInputElement)) throw new Error('not an input');
    return el.value;
  });
}

async function addTime(value: string, commit: 'blur' | 'enter' = 'blur') {
  fireEvent.click(addButton());
  const n = shownTimes().length;
  const input = timeInput(n);
  fireEvent.change(input, { target: { value } });
  if (commit === 'enter') {
    fireEvent.keyDown(input, { key: 'Enter' });
  } else {
    fireEvent.blur(input);
  }
}

async function settled() {
  await waitFor(() => expect(addButton()).not.toBeDisabled());
}

function saved(onSave: OnSave, call: number): string[] {
  const calls = vi.mocked(onSave).mock.calls;
  const params = calls[call]?.[0];
  if (!params) throw new Error(`onSave call ${call} missing`);
  expect(params.key).toBe('scheduled_restart_times');
  return params.value;
}

describe('ScheduledRestartsSetting (Story 22.6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('empty', () => {
    it('says no restart is scheduled and offers Add time', () => {
      renderEcho();

      expect(screen.getByTestId('scheduled-restarts-empty')).toHaveTextContent(
        'No restart is scheduled.'
      );
      expect(addButton()).toHaveTextContent('Add time');
      expect(addButton()).not.toBeDisabled();
    });

    it.each([
      ['server time and TZ, UTC unless set', /server time.*\(TZ\), UTC unless set/],
      ['the 15, 5 and 1 minute warnings', /warned in chat 15, 5 and 1 minutes before/],
      ['a stopped server is not started', /stopped server is not started/],
      ['a time within 15 minutes runs the next day', /less than 15 minutes from now.*next day/],
      ['up to 24 times, 16 minutes apart', /Up to 24 times, at least 16 minutes apart/],
      ['Scheduled Jobs in browser time', /Scheduled Jobs lists.*scheduled_restart_HHMM.*browser/],
    ])('help text: %s', (_fact, pattern) => {
      renderEcho();

      expect(screen.getByText(pattern)).toBeInTheDocument();
    });
  });

  describe('saving (AC 2)', () => {
    it('saves the whole list once per step, in order', async () => {
      const onSave = renderEcho();

      await addTime('04:00');
      await settled();
      await addTime('16:00', 'enter');
      await settled();
      // Enter then blur on the same edit: one save
      fireEvent.blur(timeInput(2));
      await settled();
      fireEvent.change(timeInput(2), { target: { value: '18:30' } });
      fireEvent.blur(timeInput(2));
      await settled();
      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 04:00' }));
      await settled();

      expect(onSave).toHaveBeenCalledTimes(4);
      expect(saved(onSave, 0)).toEqual(['04:00']);
      expect(saved(onSave, 1)).toEqual(['04:00', '16:00']);
      expect(saved(onSave, 2)).toEqual(['04:00', '18:30']);
      expect(saved(onSave, 3)).toEqual(['18:30']);
      expect(shownTimes()).toEqual(['18:30']);
    });

    it('sends the list sorted and shows the rows sorted', async () => {
      const onSave = renderEcho(['04:00']);

      await addTime('02:00');
      await settled();

      expect(saved(onSave, 0)).toEqual(['02:00', '04:00']);
      expect(shownTimes()).toEqual(['02:00', '04:00']);
    });
  });

  describe('no save', () => {
    it('Add time then a blur of the empty input', async () => {
      const onSave = renderEcho();

      fireEvent.click(addButton());
      fireEvent.blur(timeInput(1));

      expect(onSave).not.toHaveBeenCalled();
      expect(shownTimes()).toEqual(['']);
    });

    it('a blur with an unchanged value', () => {
      const onSave = renderEcho(['04:00']);

      fireEvent.focus(timeInput(1));
      fireEvent.blur(timeInput(1));
      fireEvent.keyDown(timeInput(1), { key: 'Enter' });

      expect(onSave).not.toHaveBeenCalled();
    });

    it('Remove of a new empty row', () => {
      const onSave = renderEcho(['04:00']);

      fireEvent.click(addButton());
      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 2' }));

      expect(onSave).not.toHaveBeenCalled();
      expect(shownTimes()).toEqual(['04:00']);
    });

    it('Remove of a new row whose time was refused: the message goes', async () => {
      const onSave = renderEcho(['04:00']);

      await addTime('04:10');
      expect(screen.getByRole('alert')).toHaveTextContent(GAP_MESSAGE);

      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 04:10' }));

      expect(onSave).not.toHaveBeenCalled();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(shownTimes()).toEqual(['04:00']);
    });
  });

  describe('refused before sending (AC 3)', () => {
    it.each([
      ['a time 10 minutes from another', ['04:00'], '04:10', GAP_MESSAGE],
      [
        'two times 10 minutes apart across midnight',
        ['00:05'],
        '23:55',
        "'23:55' and '00:05' are 10 minutes apart; restart times must be at least 16 minutes apart",
      ],
      ['the same time twice', ['04:00'], '04:00', "'04:00' is already in the list"],
    ])('%s', async (_name, initial, added, message) => {
      const onSave = renderEcho(initial);

      await addTime(added);

      const alert = screen.getByRole('alert');
      expect(alert).toHaveTextContent(message);
      expect(alert).toHaveAttribute('id', 'scheduled_restart_times-error');
      expect(onSave).not.toHaveBeenCalled();
      expect(shownTimes()).toEqual([...initial, added]);
      for (const n of [1, 2]) {
        expect(timeInput(n)).toHaveAttribute('aria-invalid', 'true');
        expect(timeInput(n)).toHaveAttribute('aria-describedby', 'scheduled_restart_times-error');
      }
    });

    it('a saved time cleared to empty', () => {
      const onSave = renderEcho(['04:00']);

      fireEvent.change(timeInput(1), { target: { value: '' } });
      fireEvent.blur(timeInput(1));

      expect(screen.getByRole('alert')).toHaveTextContent('Enter a time, or remove it');
      expect(onSave).not.toHaveBeenCalled();
      expect(shownTimes()).toEqual(['']);
    });

    it('an edit that makes the list valid clears the message', async () => {
      renderEcho(['04:00']);

      await addTime('04:10');
      fireEvent.change(timeInput(2), { target: { value: '05:00' } });

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('disables Add time at 24 times and says why', () => {
      const times = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
      renderEcho(times);

      expect(addButton()).toBeDisabled();
      expect(screen.getByTestId('scheduled-restarts-max')).toHaveTextContent(
        'At most 24 restart times.'
      );
    });

    describe('counts only filled times toward 24 (review)', () => {
      const hourly23 = Array.from({ length: 23 }, (_, i) => `${String(i).padStart(2, '0')}:00`);

      it('with 23 times and a new empty row, Add time stays enabled', () => {
        renderEcho(hourly23);

        fireEvent.click(addButton());

        expect(shownTimes()).toHaveLength(24);
        expect(addButton()).not.toBeDisabled();
        expect(screen.queryByTestId('scheduled-restarts-max')).not.toBeInTheDocument();
      });

      it('filling the 24th time disables Add time', async () => {
        const onSave = renderEcho(hourly23);

        await addTime('23:00');

        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(saved(onSave, 0)).toHaveLength(24);
        await waitFor(() => expect(addButton()).toBeDisabled());
        expect(screen.getByTestId('scheduled-restarts-max')).toHaveTextContent(
          'At most 24 restart times.'
        );
      });

      it('an empty row can never make 25: filling it is refused and nothing is sent', async () => {
        const onSave = renderEcho(hourly23);

        fireEvent.click(addButton());
        fireEvent.click(addButton());
        expect(shownTimes()).toHaveLength(25);
        fireEvent.change(timeInput(24), { target: { value: '23:00' } });
        fireEvent.blur(timeInput(24));
        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(addButton()).toBeDisabled());

        fireEvent.change(timeInput(25), { target: { value: '23:30' } });
        fireEvent.blur(timeInput(25));

        expect(screen.getByRole('alert')).toHaveTextContent('at most 24 times, got 25');
        expect(onSave).toHaveBeenCalledTimes(1);
      });
    });

    it('describes the inputs by the help text when there is no message', () => {
      renderEcho(['04:00']);

      expect(timeInput(1)).not.toHaveAttribute('aria-invalid', 'true');
      expect(timeInput(1)).toHaveAttribute('aria-describedby', 'scheduled_restart_times-desc');
      expect(screen.queryByTestId('scheduled-restarts-max')).not.toBeInTheDocument();
    });
  });

  describe('a failed save (AC 4)', () => {
    it("shows the API's message and keeps the edited rows; a later save clears it", async () => {
      const onSave = vi
        .fn()
        .mockRejectedValueOnce(new Error(SERVER_MESSAGE))
        .mockResolvedValue(undefined);
      render(<ScheduledRestartsSetting times={['08:00']} onSave={onSave} />);

      await addTime('04:00');
      await settled();

      expect(screen.getByRole('alert')).toHaveTextContent(SERVER_MESSAGE);
      expect(shownTimes()).toEqual(['08:00', '04:00']);

      fireEvent.change(timeInput(2), { target: { value: '05:00' } });
      fireEvent.blur(timeInput(2));
      await settled();

      expect(onSave).toHaveBeenCalledTimes(2);
      expect(saved(onSave, 1)).toEqual(['05:00', '08:00']);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('shows the message of a not-applied save and the saved list', async () => {
      const notApplied = 'Saved, but the restart jobs could not be applied';
      const onSave = vi
        .fn()
        .mockRejectedValue(new ApiError('API_SETTING_NOT_APPLIED', notApplied, 500));
      render(<ScheduledRestartsSetting times={['08:00']} onSave={onSave} />);

      await addTime('04:00');
      await settled();

      expect(screen.getByRole('alert')).toHaveTextContent(notApplied);
      expect(shownTimes()).toEqual(['04:00', '08:00']);

      // A blur that changes nothing keeps the server's message
      fireEvent.focus(timeInput(1));
      fireEvent.blur(timeInput(1));
      expect(screen.getByRole('alert')).toHaveTextContent(notApplied);
      expect(onSave).toHaveBeenCalledTimes(1);
    });

    // Controller decision (2026-11-19), for the maintainer to review: decision 2
    it('does not send an unchanged list again after a failure; a row change does', async () => {
      const onSave = vi.fn().mockRejectedValue(new Error(SERVER_MESSAGE));
      render(<ScheduledRestartsSetting times={['08:00']} onSave={onSave} />);

      await addTime('04:00');
      await settled();
      fireEvent.focus(timeInput(2));
      fireEvent.blur(timeInput(2));
      fireEvent.keyDown(timeInput(1), { key: 'Enter' });
      await settled();

      expect(onSave).toHaveBeenCalledTimes(1);

      fireEvent.change(timeInput(2), { target: { value: '05:00' } });
      fireEvent.change(timeInput(2), { target: { value: '04:00' } });
      fireEvent.blur(timeInput(2));
      await settled();

      expect(onSave).toHaveBeenCalledTimes(2);
      expect(saved(onSave, 1)).toEqual(['04:00', '08:00']);
    });

    // Controller decision (2026-11-19), for the maintainer to review: decision 3
    it("clears the server's message when the rows return to the saved list", async () => {
      const onSave = vi.fn().mockRejectedValue(new Error(SERVER_MESSAGE));
      render(<ScheduledRestartsSetting times={['08:00']} onSave={onSave} />);

      fireEvent.change(timeInput(1), { target: { value: '09:00' } });
      fireEvent.blur(timeInput(1));
      await settled();
      expect(screen.getByRole('alert')).toHaveTextContent(SERVER_MESSAGE);

      // Another edit that is not the saved list keeps it
      fireEvent.change(timeInput(1), { target: { value: '10:00' } });
      expect(screen.getByRole('alert')).toHaveTextContent(SERVER_MESSAGE);

      fireEvent.change(timeInput(1), { target: { value: '08:00' } });
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      fireEvent.blur(timeInput(1));
      expect(onSave).toHaveBeenCalledTimes(1);
    });

    // Controller decision (2026-11-19), for the maintainer to review: decision 3
    it("clears the server's message when a Remove brings back the saved list", async () => {
      const onSave = vi.fn().mockRejectedValue(new Error(SERVER_MESSAGE));
      render(<ScheduledRestartsSetting times={['08:00']} onSave={onSave} />);

      await addTime('04:00');
      await settled();
      expect(screen.getByRole('alert')).toHaveTextContent(SERVER_MESSAGE);

      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 04:00' }));

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(shownTimes()).toEqual(['08:00']);
      expect(onSave).toHaveBeenCalledTimes(1);
    });
  });

  describe('removing the last time (AC 5)', () => {
    it('saves [] and says no restart is scheduled', async () => {
      const onSave = renderEcho(['04:00']);

      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 04:00' }));
      await settled();

      expect(onSave).toHaveBeenCalledTimes(1);
      expect(saved(onSave, 0)).toEqual([]);
      expect(screen.getByTestId('scheduled-restarts-empty')).toBeInTheDocument();
    });
  });

  describe('while a save is pending', () => {
    it('disables the inputs and Add time', async () => {
      const { onSave, resolvers } = deferredSave();
      renderEcho(['04:00'], onSave);

      fireEvent.change(timeInput(1), { target: { value: '05:00' } });
      fireEvent.blur(timeInput(1));

      expect(timeInput(1)).toBeDisabled();
      expect(addButton()).toBeDisabled();

      await act(async () => resolvers[0]?.resolve());
      await settled();
      expect(timeInput(1)).not.toBeDisabled();
    });

    // Controller decision (2026-11-19), for the maintainer to review: decision 1
    it('a blur and a Remove in one gesture: the Remove waits, then saves', async () => {
      const { onSave, resolvers } = deferredSave();
      renderEcho(['04:00', '08:00'], onSave);

      fireEvent.change(timeInput(2), { target: { value: '09:00' } });
      // Clicking Remove takes the focus from the edited input first
      fireEvent.blur(timeInput(2));
      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 04:00' }));

      expect(onSave).toHaveBeenCalledTimes(1);
      expect(saved(onSave, 0)).toEqual(['04:00', '09:00']);

      await act(async () => resolvers[0]?.resolve());
      await waitFor(() => expect(onSave).toHaveBeenCalledTimes(2));
      expect(saved(onSave, 1)).toEqual(['09:00']);

      await act(async () => resolvers[1]?.resolve());
      await settled();
      expect(shownTimes()).toEqual(['09:00']);
    });
  });

  describe('following the times prop', () => {
    it('shows new times while idle', () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const { rerender } = render(<ScheduledRestartsSetting times={['04:00']} onSave={onSave} />);

      rerender(<ScheduledRestartsSetting times={['16:00', '06:00']} onSave={onSave} />);

      expect(shownTimes()).toEqual(['06:00', '16:00']);
    });

    it('keeps the edited rows while a message is shown', async () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const { rerender } = render(<ScheduledRestartsSetting times={['04:00']} onSave={onSave} />);

      await addTime('04:10');
      rerender(<ScheduledRestartsSetting times={['12:00']} onSave={onSave} />);

      expect(shownTimes()).toEqual(['04:00', '04:10']);
      expect(screen.getByRole('alert')).toHaveTextContent(GAP_MESSAGE);
    });

    // Controller decision (2026-11-19), for the maintainer to review: decision 4
    it('keeps a new row the admin has not filled in', () => {
      const onSave = vi.fn().mockResolvedValue(undefined);
      const { rerender } = render(<ScheduledRestartsSetting times={['04:00']} onSave={onSave} />);

      fireEvent.click(addButton());
      fireEvent.blur(timeInput(2));
      rerender(<ScheduledRestartsSetting times={['06:00', '12:00']} onSave={onSave} />);

      expect(shownTimes()).toEqual(['06:00', '12:00', '']);
    });
  });

  describe('accessibility (AC 8)', () => {
    it('names each input and Remove button', () => {
      renderEcho(['04:00']);

      fireEvent.click(addButton());

      expect(timeInput(1)).toHaveValue('04:00');
      expect(timeInput(2)).toHaveValue('');
      expect(screen.getByRole('button', { name: 'Remove restart time 04:00' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Remove restart time 2' })).toBeInTheDocument();
      expect(screen.getByRole('list', { name: 'Restart times' })).toBeInTheDocument();
      expect(timeInput(1)).toHaveAttribute('type', 'time');
      expect(timeInput(1)).toHaveAttribute('step', '60');
    });

    it('focuses the new input after Add time', () => {
      renderEcho(['04:00']);

      fireEvent.click(addButton());

      expect(document.activeElement).toBe(timeInput(2));
    });

    it('after a Remove has saved, focuses the next input, else the previous, else Add time', async () => {
      const { onSave, resolvers } = deferredSave();
      renderEcho(['04:00', '08:00', '12:00'], onSave);

      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 08:00' }));
      expect(document.activeElement).not.toBe(timeInput(2));
      await act(async () => resolvers[0]?.resolve());
      await settled();
      expect(document.activeElement).toBe(timeInput(2));
      expect(timeInput(2)).toHaveValue('12:00');

      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 12:00' }));
      await act(async () => resolvers[1]?.resolve());
      await settled();
      expect(document.activeElement).toBe(timeInput(1));

      fireEvent.click(screen.getByRole('button', { name: 'Remove restart time 04:00' }));
      await act(async () => resolvers[2]?.resolve());
      await settled();
      expect(document.activeElement).toBe(addButton());
    });

    it('gives the new controls 44px below 1024px (classes; heights are measured in E2E)', () => {
      renderEcho(['04:00']);

      expect(addButton()).toHaveClass('max-lg:min-h-11');
      expect(screen.getByTestId('remove-restart-time-1')).toHaveClass('max-lg:size-11');
      expect(screen.getByTestId('restart-time-1')).toHaveClass('max-lg:h-11');
    });
  });
});
