/**
 * Zustand store for UI-only state.
 * Server state is managed by TanStack Query, not here.
 */
import { create } from 'zustand';

interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  // Company detail drawer
  selectedCompanyId: string | null;
  openCompanyDrawer: (id: string) => void;
  closeCompanyDrawer: () => void;

  // Review detail
  selectedReviewItemId: string | null;
  selectReviewItem: (id: string | null) => void;

  // Toast messages
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

let toastCounter = 0;

export const useStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  selectedCompanyId: null,
  openCompanyDrawer: (id) => set({ selectedCompanyId: id }),
  closeCompanyDrawer: () => set({ selectedCompanyId: null }),

  selectedReviewItemId: null,
  selectReviewItem: (id) => set({ selectedReviewItemId: id }),

  toasts: [],
  addToast: (toast) => {
    const id = `toast-${++toastCounter}`;
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
    if (toast.type !== 'error') {
      setTimeout(() => {
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
      }, 5000);
    }
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
