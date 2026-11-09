import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/api/query-client';
import { reloadForStaleChunk } from '@/lib/stale-chunk-reload';
import App from './App.tsx';
import './styles/index.css';

window.addEventListener('vite:preloadError', () => reloadForStaleChunk());

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
