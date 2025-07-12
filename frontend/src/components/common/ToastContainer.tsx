import React from 'react';
import { AnimatePresence } from 'framer-motion';
import { useToastStore } from '../../store/toastStore';
import Toast from './Toast';

const ToastContainer: React.FC = () => {
  const { toasts } = useToastStore();

  return (
    <div className="fixed top-4 right-4 z-[9999] space-y-2">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
};

export default ToastContainer;