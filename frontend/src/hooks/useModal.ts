/**
 * useModal Hook
 * 
 * Custom hook for managing modal dialogs.
 */

import { useState, useCallback } from 'react';

export interface ModalConfig {
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'default' | 'danger';
  showCancel?: boolean;
  onConfirm?: () => void;
}

export const useModal = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState<ModalConfig>({
    title: '',
  });

  const openModal = useCallback((modalConfig: ModalConfig) => {
    setConfig(modalConfig);
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsOpen(false);
  }, []);

  const confirm = useCallback(
    (
      title: string,
      message?: string,
      onConfirm?: () => void,
      variant: 'default' | 'danger' = 'default'
    ) => {
      return new Promise<boolean>((resolve) => {
        openModal({
          title,
          message,
          variant,
          showCancel: true,
          onConfirm: () => {
            if (onConfirm) onConfirm();
            resolve(true);
          },
        });
      });
    },
    [openModal]
  );

  return {
    isOpen,
    config,
    openModal,
    closeModal,
    confirm,
  };
};

// Made with Bob
