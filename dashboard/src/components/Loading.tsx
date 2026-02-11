'use client';

import React from 'react';
import { RefreshCw, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  return (
    <Loader2
      className={cn(
        'animate-spin text-vanguard-400',
        sizeClasses[size],
        className
      )}
    />
  );
};

interface RefreshButtonProps {
  onClick: () => void;
  loading?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const RefreshButton: React.FC<RefreshButtonProps> = ({
  onClick,
  loading = false,
  className,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={cn(
        'p-2 rounded-lg bg-surface-2 hover:bg-surface-2/80 transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      title="Refresh data"
    >
      <RefreshCw
        className={cn(
          sizeClasses[size],
          loading && 'animate-spin'
        )}
      />
    </button>
  );
};