import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { useEffect } from 'react';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  width?: string;
}

export function Drawer({ open, onClose, title, children, width = 'w-[60vw] max-w-4xl' }: DrawerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (open) document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      {/* Panel */}
      <div
        className={cn(
          'fixed top-0 right-0 z-50 h-full bg-white shadow-xl border-l border-slate-200 overflow-y-auto',
          width,
        )}
      >
        {title && (
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100">
              <X className="h-5 w-5 text-slate-500" />
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </>
  );
}
