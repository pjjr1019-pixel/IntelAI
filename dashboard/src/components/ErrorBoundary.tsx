'use client';

import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 bg-surface-1 rounded-xl border border-red-500/20">
          <AlertTriangle className="w-12 h-12 text-red-400 mb-4" />
          <h3 className="text-lg font-semibold text-red-400 mb-2">Something went wrong</h3>
          <p className="text-muted-foreground text-center mb-4">
            An unexpected error occurred. Please try refreshing the page.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 px-4 py-2 bg-vanguard-600 hover:bg-vanguard-700 text-white rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh Page
          </button>
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-4 w-full">
              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                Error Details (Development)
              </summary>
              <pre className="mt-2 p-2 bg-black/20 rounded text-xs overflow-auto">
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}