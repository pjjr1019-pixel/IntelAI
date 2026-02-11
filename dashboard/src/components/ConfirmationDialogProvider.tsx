'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { ConfirmationDialog } from '@/components/ConfirmationDialog';
import { useConfirmation } from '@/hooks/useConfirmation';

interface ConfirmationContextType {
  confirm: (options: {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    type?: 'danger' | 'warning' | 'info';
  }) => Promise<boolean>;
}

const ConfirmationContext = createContext<ConfirmationContextType | undefined>(undefined);

export const useConfirmationDialog = () => {
  const context = useContext(ConfirmationContext);
  if (!context) {
    throw new Error('useConfirmationDialog must be used within a ConfirmationDialogProvider');
  }
  return context;
};

interface ConfirmationDialogProviderProps {
  children: ReactNode;
}

export const ConfirmationDialogProvider: React.FC<ConfirmationDialogProviderProps> = ({ children }) => {
  const { confirmation, confirm } = useConfirmation();

  return (
    <ConfirmationContext.Provider value={{ confirm }}>
      {children}
      {confirmation && (
        <ConfirmationDialog
          isOpen={confirmation.isOpen}
          title={confirmation.title}
          message={confirmation.message}
          confirmText={confirmation.confirmText}
          cancelText={confirmation.cancelText}
          onConfirm={confirmation.onConfirm}
          onCancel={confirmation.onCancel}
          type={confirmation.type}
        />
      )}
    </ConfirmationContext.Provider>
  );
};