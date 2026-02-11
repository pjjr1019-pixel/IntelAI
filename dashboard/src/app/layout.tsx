import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'
import { ToastProvider } from '@/components/ToastProvider'
import { ConfirmationDialogProvider } from '@/components/ConfirmationDialogProvider'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ThemeProvider } from '@/components/ThemeProvider'
import { UserPreferencesProvider } from '@/components/UserPreferencesProvider'
import { KeyboardShortcutsProvider } from '@/components/KeyboardShortcutsProvider'
import { DashboardLayoutProvider } from '@/components/DashboardLayoutProvider'
import { MobileMenuProvider } from '@/components/MobileMenuProvider'
import { SidebarProvider, useSidebar } from '@/components/SidebarProvider'
import { SettingsProvider } from '@/components/SettingsProvider'
import { ServiceWorkerManager } from '@/components/ServiceWorker'
import { MainContent } from '@/components/MainContent'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Intel-AI — Pre-Event Anomaly Detection',
  description: 'OSINT & Predictive Intelligence Dashboard',
  manifest: '/manifest.json',
  icons: {
    icon: '/icon-192.svg',
    apple: '/icon-192.svg',
  },
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0f172a',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-background">
        {/* Skip to main content link for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-vanguard-600 text-white px-4 py-2 rounded-lg z-50"
        >
          Skip to main content
        </a>
        
        <ThemeProvider>
          <UserPreferencesProvider>
            <SettingsProvider>
              <KeyboardShortcutsProvider>
                <DashboardLayoutProvider>
                  <MobileMenuProvider>
                    <SidebarProvider>
                      <Sidebar />
                      <MainContent>
                        {children}
                      </MainContent>
                    </SidebarProvider>
                  </MobileMenuProvider>
                </DashboardLayoutProvider>
              </KeyboardShortcutsProvider>
            </SettingsProvider>
          </UserPreferencesProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}