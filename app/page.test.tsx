import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';

import Home from './page';

afterEach(cleanup);

/**
 * The sample result is a hardcoded placeholder. None of its figures may ever be
 * presented as the outcome of a real investigation.
 */
const FABRICATED_FIGURE = /\$428,400/;
const FABRICATED_ANSWER = /Enterprise Analytics drove the largest/;

async function investigateWithFailingBackend(failure: () => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(failure));
  render(<Home />);

  // The suggestion buttons call investigate() directly with their own question.
  screen.getByRole('button', { name: /What changed in churn/ }).click();

  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
}

test('a failed investigation does not present sample figures as evidence', async () => {
  await investigateWithFailingBackend(() => Promise.reject(new TypeError('network down')));

  await waitFor(() => {
    expect(screen.queryByText(FABRICATED_ANSWER)).toBeNull();
    expect(screen.queryByText(FABRICATED_FIGURE)).toBeNull();
  });
});

test('a 502 from the backend does not present sample figures as evidence', async () => {
  await investigateWithFailingBackend(() =>
    Promise.resolve(new Response('{"detail":"nope"}', { status: 502 })),
  );

  await waitFor(() => {
    expect(screen.queryByText(FABRICATED_ANSWER)).toBeNull();
    expect(screen.queryByText(FABRICATED_FIGURE)).toBeNull();
  });
});

test('a failed investigation reports the failure and shows no evidence rows', async () => {
  await investigateWithFailingBackend(() => Promise.reject(new TypeError('network down')));

  await waitFor(() => {
    expect(screen.getByText(/0 evidence rows/)).toBeTruthy();
    expect(screen.getByText(/no evidence to show/i)).toBeTruthy();
    expect(screen.getByText(/no evidence retrieved/i)).toBeTruthy();
    expect(screen.queryByText(/Evidence checked/)).toBeNull();
  });
});

test('a failed investigation does not claim the trace completed or that queries were guarded', async () => {
  await investigateWithFailingBackend(() => Promise.reject(new TypeError('network down')));

  await waitFor(() => {
    expect(screen.getByText(/0 steps/)).toBeTruthy();
    expect(screen.queryByText(/Investigation complete/)).toBeNull();
    expect(screen.queryByText(/Deterministic demo agent/)).toBeNull();
    // No queries ran, so nothing was validated or row-limited.
    expect(screen.queryByText(/Safe execution/)).toBeNull();
  });
});

test('a successful investigation still reports the completed trace', async () => {
  const payload = {
    question: 'Which region has the highest average order value?',
    answer: 'Southeast leads at $1,579.18.',
    columns: ['region'],
    evidence: [{ region: 'Southeast' }],
    trace: [
      { id: 1, title: 'Executed read-only query', detail: 'Returned 4 rows', duration_ms: 8, tool: 'execute_sql', status: 'complete' },
    ],
    mode: 'demo',
  };
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }))));
  render(<Home />);

  screen.getByRole('button', { name: /Which region has the highest/ }).click();

  await waitFor(() => {
    expect(screen.getByText(/Investigation complete/)).toBeTruthy();
    expect(screen.getByText(/Deterministic demo agent/)).toBeTruthy();
    expect(screen.getByText(/Safe execution/)).toBeTruthy();
    expect(screen.getByText(/Evidence checked/)).toBeTruthy();
  });
});
