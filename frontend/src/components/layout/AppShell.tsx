import { Outlet, useParams } from 'react-router-dom';
import { TopBar } from './TopBar';
import { WorkflowRail } from './WorkflowRail';

export function AppShell() {
  const { runId } = useParams();
  const showRail = !!runId;

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        {showRail && <WorkflowRail />}
        <main className="flex-1 overflow-y-auto bg-slate-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
