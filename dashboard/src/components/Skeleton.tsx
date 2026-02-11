'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className }) => {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-surface-2/50",
        className
      )}
    />
  );
};

export const SkeletonCard: React.FC<SkeletonProps> = ({ className }) => {
  return (
    <div className={cn("p-6 bg-surface-1 rounded-xl border border-white/[0.06]", className)}>
      <div className="space-y-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-8 w-1/2" />
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    </div>
  );
};

export const SkeletonTable: React.FC<SkeletonProps> = ({ className }) => {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex gap-4">
        <Skeleton className="h-4 flex-1" />
        <Skeleton className="h-4 flex-1" />
        <Skeleton className="h-4 flex-1" />
        <Skeleton className="h-4 w-20" />
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  );
};

export const SkeletonChart: React.FC<SkeletonProps> = ({ className }) => {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex justify-between">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-6 w-24" />
      </div>
      <Skeleton className="h-64 w-full rounded-lg" />
      <div className="flex justify-center gap-4">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
};

export const SkeletonText: React.FC<{ lines?: number } & SkeletonProps> = ({
  lines = 3,
  className
}) => {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            "h-4",
            i === lines - 1 ? "w-3/4" : "w-full" // Last line shorter
          )}
        />
      ))}
    </div>
  );
};

export const SkeletonButton: React.FC<SkeletonProps> = ({ className }) => {
  return <Skeleton className={cn("h-10 w-24", className)} />;
};

export const SkeletonInput: React.FC<SkeletonProps> = ({ className }) => {
  return <Skeleton className={cn("h-10 w-full", className)} />;
};