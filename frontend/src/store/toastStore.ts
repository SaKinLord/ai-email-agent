import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

const generateId = () => Math.random().toString(36).substr(2, 9);

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  
  addToast: (toast) => {
    const id = generateId();
    const newToast: Toast = {
      id,
      duration: 5000, // 5 seconds default
      ...toast,
    };
    
    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));
    
    // Auto remove after duration
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, newToast.duration);
    }
  },
  
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    }));
  },
  
  clearToasts: () => {
    set({ toasts: [] });
  },
}));

// Helper functions for common toast types
export const toast = {
  success: (title: string, message?: string, action?: Toast['action']) => {
    useToastStore.getState().addToast({ 
      type: 'success', 
      title, 
      message, 
      action 
    });
  },
  
  error: (title: string, message?: string, action?: Toast['action']) => {
    useToastStore.getState().addToast({ 
      type: 'error', 
      title, 
      message, 
      action,
      duration: 8000 // Longer duration for errors
    });
  },
  
  warning: (title: string, message?: string, action?: Toast['action']) => {
    useToastStore.getState().addToast({ 
      type: 'warning', 
      title, 
      message, 
      action 
    });
  },
  
  info: (title: string, message?: string, action?: Toast['action']) => {
    useToastStore.getState().addToast({ 
      type: 'info', 
      title, 
      message, 
      action 
    });
  },
};