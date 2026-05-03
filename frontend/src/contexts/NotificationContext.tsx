/**
 * Notification Context
 * 
 * Provides toast and modal functionality throughout the application.
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { useToast } from '../hooks/useToast';
import { useModal } from '../hooks/useModal';
import { ToastContainer } from '../components/common';
import Modal from '../components/common/Modal';

interface NotificationContextType {
  // Toast methods
  showSuccess: (title: string, message?: string, duration?: number) => void;
  showError: (title: string, message?: string, duration?: number) => void;
  showWarning: (title: string, message?: string, duration?: number) => void;
  showInfo: (title: string, message?: string, duration?: number) => void;
  
  // Modal methods
  showConfirm: (
    title: string,
    message?: string,
    onConfirm?: () => void,
    variant?: 'default' | 'danger'
  ) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(
  undefined
);

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error(
      'useNotification must be used within a NotificationProvider'
    );
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({
  children,
}) => {
  const { toasts, removeToast, success, error, warning, info } = useToast();
  const { isOpen, config, openModal, closeModal } = useModal();

  const showSuccess = (title: string, message?: string, duration?: number) => {
    success(title, message, duration);
  };

  const showError = (title: string, message?: string, duration?: number) => {
    error(title, message, duration);
  };

  const showWarning = (title: string, message?: string, duration?: number) => {
    warning(title, message, duration);
  };

  const showInfo = (title: string, message?: string, duration?: number) => {
    info(title, message, duration);
  };

  const showConfirm = (
    title: string,
    message?: string,
    onConfirm?: () => void,
    variant: 'default' | 'danger' = 'default'
  ) => {
    openModal({
      title,
      message,
      variant,
      showCancel: true,
      onConfirm,
    });
  };

  const value: NotificationContextType = {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showConfirm,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onClose={removeToast} />
      <Modal
        isOpen={isOpen}
        onClose={closeModal}
        title={config.title}
        message={config.message}
        confirmText={config.confirmText}
        cancelText={config.cancelText}
        variant={config.variant}
        showCancel={config.showCancel}
        onConfirm={config.onConfirm}
      />
    </NotificationContext.Provider>
  );
};

// Made with Bob
