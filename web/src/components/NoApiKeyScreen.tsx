import { KeyRound } from 'lucide-react';

interface NoApiKeyScreenProps {
  /** Whether the page runs on the Vite dev server, which takes its key from VITE_API_KEY. */
  devServer?: boolean;
}

/**
 * Full-page set-up message shown instead of the app when the web UI has no API key
 * (Story 19.2, FR210, Epic 19 ADR-5). Fixed text only; it calls nothing.
 */
export function NoApiKeyScreen({ devServer = import.meta.env.DEV }: NoApiKeyScreenProps) {
  return (
    <main
      className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center text-foreground"
      data-testid="no-api-key-screen"
    >
      <KeyRound className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden="true" />
      <h1 className="mb-4 text-2xl font-semibold">No API key configured</h1>
      <div className="max-w-lg space-y-4 text-muted-foreground">
        <p>
          The web UI was not given an API key, so it cannot talk to the server. Set{' '}
          <code>VS_API_KEY</code> on the server and restart it:
        </p>
        <ul className="list-inside list-disc text-left">
          <li>
            the Monitor key (<code>VS_API_KEY_MONITOR</code>) for a read-only web UI
          </li>
          <li>
            the Admin key (<code>VS_API_KEY_ADMIN</code>) for full access
          </li>
        </ul>
        <p>Anyone who can open this page receives that key.</p>
        {devServer && (
          <p data-testid="no-api-key-dev-hint">
            Running the Vite dev server? Set <code>VITE_API_KEY</code> in <code>web/.env</code>.
          </p>
        )}
      </div>
    </main>
  );
}
