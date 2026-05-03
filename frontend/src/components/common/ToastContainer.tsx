/**
 * Toast Container Component
 * 
 * Container for managing and displaying multiple toast notifications.
 */

import React from 'react';
import Toast, { ToastProps } from './Toast';

export interface ToastContainerProps {
  toasts: Omit<ToastProps, 'onClose'>[];
  onClose: (id: string) => void;
}

const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onClose }) => {
  return (
    <div
      className="fixed top-20 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center pointer-events-none"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="pointer-events-auto">
        {toasts.map((toast) => (
          <Toast key={toast.id} {...toast} onClose={onClose} />
        ))}
      </div>
    </div>
  );
};

export default ToastContainer;

// Made with Bob
