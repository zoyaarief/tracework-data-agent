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
