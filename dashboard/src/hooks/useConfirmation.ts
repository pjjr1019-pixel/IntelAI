'use client';

import { useState, useCallback } from 'react';

interface ConfirmationOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info';
}

interface ConfirmationState extends ConfirmationOptions {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const useConfirmation = () => {
  const [confirmation, setConfirmation] = useState<ConfirmationState | null>(null);

  const confirm = useCallback((options: ConfirmationOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      const handleConfirm = () => {
        setConfirmation(null);
        resolve(true);
      };

      const handleCancel = () => {
        setConfirmation(null);
        resolve(false);
      };

      setConfirmation({
        ...options,
        isOpen: true,
        onConfirm: handleConfirm,
        onCancel: handleCancel,
      });
    });
  }, []);

  const close = useCallback(() => {
    setConfirmation(null);
  }, []);

  return {
    confirmation,
    confirm,
    close,
  };
};