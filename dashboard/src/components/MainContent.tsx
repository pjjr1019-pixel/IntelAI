'use client';

import { useSidebar } from '@/components/SidebarProvider';
import { GlobalKeyboardShortcuts } from '@/components/GlobalKeyboardShortcuts';
import { ServiceWorkerManager } from '@/components/ServiceWorker';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ToastProvider } from '@/components/ToastProvider';
import { ConfirmationDialogProvider } from '@/components/ConfirmationDialogProvider';

export function MainContent({ children }: { children: React.ReactNode }) {
  const { isSidebarVisible } = useSidebar();

  return (
    <main id="main-content" className={`flex-1 ml-0 md:ml-0 pl-6 pr-6 pt-8 pb-8 md:pl-8 md:pr-8 md:pt-8 md:pb-8 overflow-auto relative min-h-screen transition-all duration-300 ease-in-out ${isSidebarVisible ? 'md:ml-64' : 'md:ml-0'}`}>
      <div className="fixed top-0 right-0 w-96 h-96 bg-primary/3 rounded-full blur-3xl pointer-events-none dark:bg-primary/5"></div>
      <div className="fixed bottom-0 left-64 w-80 h-80 bg-accent/3 rounded-full blur-3xl pointer-events-none dark:bg-accent/5"></div>
      <div className="relative z-10 max-w-7xl mx-auto">
        <GlobalKeyboardShortcuts />
        <ServiceWorkerManager />
        <ErrorBoundary>
          <ToastProvider>
            <ConfirmationDialogProvider>
              {children}
            </ConfirmationDialogProvider>
          </ToastProvider>
        </ErrorBoundary>
      </div>
    </main>
  );
}