import { useStore } from '@/hooks/useStore';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

const typeStyles = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

export function ToastContainer() {
  const toasts = useStore((s) => s.toasts);
  const removeToast = useStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn('flex items-center gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg', typeStyles[t.type])}
        >
          <span className="flex-1">{t.message}</span>
          <button onClick={() => removeToast(t.id)} className="shrink-0 opacity-60 hover:opacity-100">
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
