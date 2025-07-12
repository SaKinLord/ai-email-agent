import { Toast, ToastType } from '../store/toastStore';

export const createToast = (
  title: string,
  type: ToastType = 'info',
  message?: string,
  duration?: number,
  action?: { label: string; onClick: () => void }
): Omit<Toast, 'id'> => ({
  title,
  type,
  message,
  duration,
  action
});

// Convenience functions for common toast types
export const successToast = (
  title: string,
  message?: string,
  duration?: number,
  action?: { label: string; onClick: () => void }
) => createToast(title, 'success', message, duration, action);

export const errorToast = (
  title: string,
  message?: string,
  duration?: number,
  action?: { label: string; onClick: () => void }
) => createToast(title, 'error', message, duration, action);

export const warningToast = (
  title: string,
  message?: string,
  duration?: number,
  action?: { label: string; onClick: () => void }
) => createToast(title, 'warning', message, duration, action);

export const infoToast = (
  title: string,
  message?: string,
  duration?: number,
  action?: { label: string; onClick: () => void }
) => createToast(title, 'info', message, duration, action);