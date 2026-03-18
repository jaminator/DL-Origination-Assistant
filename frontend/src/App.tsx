import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from '@/components/layout/AppShell';
import { ToastContainer } from '@/components/ui/Toast';
import { Dashboard } from '@/pages/Dashboard';
import { RunSetup } from '@/pages/RunSetup';
import { SubVerticals } from '@/pages/SubVerticals';
import { Sources } from '@/pages/Sources';
import { Pipeline } from '@/pages/Pipeline';
import { ReviewQueue } from '@/pages/ReviewQueue';
import { Companies } from '@/pages/Companies';
import { Exports } from '@/pages/Exports';
import { Settings } from '@/pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Dashboard (no workflow rail) */}
          <Route element={<AppShell />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          {/* Run pages (with workflow rail) */}
          <Route path="/runs/:runId" element={<AppShell />}>
            <Route path="setup" element={<RunSetup />} />
            <Route path="subverticals" element={<SubVerticals />} />
            <Route path="sources" element={<Sources />} />
            <Route path="pipeline" element={<Pipeline />} />
            <Route path="review" element={<ReviewQueue />} />
            <Route path="companies" element={<Companies />} />
            <Route path="exports" element={<Exports />} />
          </Route>
        </Routes>
        <ToastContainer />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
