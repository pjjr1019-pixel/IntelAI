'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  AlertTriangle,
  Radio,
  List,
  TrendingUp,
  FlaskConical,
  Waves,
  Settings,
  Shield,
  Newspaper,
  RefreshCw,
  ExternalLink,
  BookOpen,
  Mail,
  BarChart3,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  Briefcase,
  PlayCircle,
  Zap
} from 'lucide-react';
import { api } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';
import { ThemeToggle } from './ThemeToggle';
import { memo } from 'react';
import { useSettings } from './SettingsProvider';
import { useMobileMenu } from './MobileMenuProvider';
import { useSidebar } from './SidebarProvider';

const navigation = [
  {
    name: 'Monitor',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      // { name: 'Sources', href: '/sources', icon: Radio }, // Hidden - causes 404
      // { name: 'Watchlist', href: '/watchlist', icon: List }, // Hidden - causes 404
    ],
  },
  {
    name: 'Guides',
    items: [
      { name: 'What Is Intel-AI', href: '/guides/what-is-intel-ai', icon: Zap, description: 'Simple overview of how our AI platform works and its value proposition' },
      { name: 'How It Works', href: '/guides/how-it-works', icon: BookOpen },
      { name: 'Alert Rules', href: '/guides/alert-rules', icon: AlertTriangle },
      { name: 'Signal Quality', href: '/guides/signal-quality', icon: Shield },
      { name: 'Decision Transparency', href: '/guides/decision-transparency', icon: BarChart3 },
      { name: 'Trading Survival', href: '/guides/trading-survival', icon: RefreshCw },
      { name: 'Strategy Guide (AI-Optimized)', href: '/guides/strategy-ai', icon: FlaskConical, description: 'Extremely technical, detailed guide for AI on using all app tools for maximum power and profitability.' },
      { name: 'Architecture', href: '/guides/architecture', icon: Settings },
    ],
  },
  {
    name: 'Analysis',
    items: [
      { name: 'Analytics', href: '/analytics', icon: BarChart3 },
      { name: 'Google Trends', href: '/trends', icon: TrendingUp },
      { name: 'Market Data', href: '/market-data', icon: BarChart3 },
      { name: 'News', href: '/news', icon: Newspaper },
      { name: 'Narrative Analysis', href: '/narrative', icon: Radio },
      { name: 'Portfolio', href: '/portfolio', icon: Briefcase },
      { name: 'Strategies', href: '/strategies', icon: FlaskConical },
      { name: 'Paper Trading', href: '/simulation', icon: PlayCircle },
      { name: 'Replay Mode', href: '/replay', icon: RotateCcw },
      // { name: 'Backtest', href: '/backtest', icon: FlaskConical }, // Hidden - causes 404
      // { name: 'Drift Monitor', href: '/drift', icon: Waves }, // Hidden - causes 404
    ],
  },
  {
    name: 'System',
    items: [
      { name: 'Alert Templates', href: '/alert-templates', icon: Mail },
      { name: 'Settings', href: '/settings', icon: Settings },
    ],
  },
];

interface NewsArticle {
  title: string;
  url: string;
  source: string;
  published_at: string;
  tone: number;
}

interface NewsResponse {
  articles: NewsArticle[];
  cached: boolean;
}

export function Sidebar() {
  const pathname = usePathname();
  const { isOpen: isMobileMenuOpen, setIsOpen: setIsMobileMenuOpen } = useMobileMenu();
  const { openSettings, closeSettings, isSettingsOpen } = useSettings();
  const [isGuidesOpen, setIsGuidesOpen] = useState(false);
  const [isAnalysisOpen, setIsAnalysisOpen] = useState(true); // Default open for Analysis
  const { isSidebarVisible, setIsSidebarVisible } = useSidebar();

  // WebSocket connection to API
  const wsUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, 'ws') + '/api/ws' || 'ws://127.0.0.1:8000/api/ws';
  const { isConnected } = useWebSocket(wsUrl);

  // Focus management for mobile menu
  useEffect(() => {
    if (isMobileMenuOpen) {
      // Focus the first navigation link when menu opens
      const firstLink = document.querySelector('aside[role="complementary"] nav a');
      if (firstLink instanceof HTMLElement) {
        firstLink.focus();
      }
    }
  }, [isMobileMenuOpen]);

  // Handle Escape key to close mobile menu
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isMobileMenuOpen) {
        setIsMobileMenuOpen(false);
      }
    };

    if (isMobileMenuOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isMobileMenuOpen, setIsMobileMenuOpen]);

  // Auto-hide sidebar on desktop
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      // Only apply auto-hide on desktop (screen width >= 768px)
      if (window.innerWidth >= 768) {
        const mouseX = event.clientX;
        // Show sidebar when mouse is within 50px of left edge
        if (mouseX <= 50) {
          setIsSidebarVisible(true);
        } else if (mouseX > 280) { // Hide when mouse moves away from sidebar area
          setIsSidebarVisible(false);
        }
      }
    };

    const handleMouseLeave = () => {
      // Hide sidebar when mouse leaves the window
      if (window.innerWidth >= 768) {
        setIsSidebarVisible(false);
      }
    };

    const handleResize = () => {
      // Reset sidebar visibility on window resize
      if (window.innerWidth < 768) {
        setIsSidebarVisible(false);
      }
    };

    // Add event listeners
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('resize', handleResize);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Compute sidebar transform class
  const getSidebarTransform = () => {
    if (isMobileMenuOpen) return 'translate-x-0';
    if (typeof window !== 'undefined' && window.innerWidth < 768) return '-translate-x-full';
    return isSidebarVisible ? 'translate-x-0' : '-translate-x-full';
  };

  return (
    <>
      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={`fixed inset-y-0 left-0 w-64 bg-surface-1/80 backdrop-blur-xl flex flex-col z-50 transition-transform duration-300 ease-in-out ${getSidebarTransform()}`} role="complementary" aria-label="Sidebar navigation">
      <div className="px-5 py-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-vanguard-600 to-accent-cyan flex items-center justify-center shadow-glow-sm">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-gradient">VANGUARD SIGNAL</h1>
            <p className="text-[10px] text-[var(--text-muted)] font-medium tracking-wide">ANOMALY DETECTION</p>
          </div>
        </div>
      </div>

      <nav className="px-3 py-4 space-y-5" role="navigation" aria-label="Main navigation">
        {navigation.map((section) => (
          <div key={section.name}>
            {section.name === 'Guides' ? (
              <div>
                <button
                  onClick={() => setIsGuidesOpen(!isGuidesOpen)}
                  className="flex items-center justify-between w-full px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 text-[var(--text-secondary)] hover:text-white hover:bg-white/[0.04] group"
                  aria-expanded={isGuidesOpen}
                  aria-controls="guides-menu"
                >
                  <div className="flex items-center gap-3">
                    <BookOpen className="w-5 h-5 text-[var(--text-muted)] group-hover:text-vanguard-400/70" aria-hidden="true" />
                    <span>{section.name}</span>
                  </div>
                  {isGuidesOpen ? (
                    <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                  )}
                </button>
                {isGuidesOpen && (
                  <div id="guides-menu" className="mt-1 ml-8 space-y-1 max-h-[20rem] overflow-y-auto guides-dropdown">
                    {section.items.map((item) => {
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 relative group ${
                            isActive
                              ? 'nav-active bg-vanguard-600/10 text-vanguard-400'
                              : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/[0.04]'
                          }`}
                          aria-current={isActive ? 'page' : undefined}
                        >
                          <item.icon className={`w-4 h-4 ${
                            isActive ? 'text-vanguard-400' : 'text-[var(--text-muted)] group-hover:text-vanguard-400/70'
                          }`} aria-hidden="true" />
                          {item.name}
                          {isActive && (
                            <div className="absolute right-2 w-1.5 h-1.5 rounded-full bg-vanguard-400" style={{boxShadow: '0 0 6px rgba(76, 110, 245, 0.6)'}}></div>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : section.name === 'Analysis' ? (
              <div>
                <button
                  onClick={() => setIsAnalysisOpen(!isAnalysisOpen)}
                  className="flex items-center justify-between w-full px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 text-[var(--text-secondary)] hover:text-white hover:bg-white/[0.04] group"
                  aria-expanded={isAnalysisOpen}
                  aria-controls="analysis-menu"
                >
                  <div className="flex items-center gap-3">
                    <BarChart3 className="w-5 h-5 text-[var(--text-muted)] group-hover:text-vanguard-400/70" aria-hidden="true" />
                    <span>{section.name}</span>
                  </div>
                  {isAnalysisOpen ? (
                    <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                  )}
                </button>
                {isAnalysisOpen && (
                  <div id="analysis-menu" className="mt-1 ml-8 space-y-1 max-h-[20rem] overflow-y-auto guides-dropdown">
                    {section.items.map((item) => {
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 relative group ${
                            isActive
                              ? 'nav-active bg-vanguard-600/10 text-vanguard-400'
                              : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/[0.04]'
                          }`}
                          aria-current={isActive ? 'page' : undefined}
                        >
                          <item.icon className={`w-4 h-4 ${
                            isActive ? 'text-vanguard-400' : 'text-[var(--text-muted)] group-hover:text-vanguard-400/70'
                          }`} aria-hidden="true" />
                          {item.name}
                          {isActive && (
                            <div className="absolute right-2 w-1.5 h-1.5 rounded-full bg-vanguard-400" style={{boxShadow: '0 0 6px rgba(76, 110, 245, 0.6)'}}></div>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  {section.name}
                </p>
                {section.items.map((item) => {
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 relative group ${
                        isActive
                          ? 'nav-active bg-vanguard-600/10 text-vanguard-400'
                          : 'text-[var(--text-secondary)] hover:text-white hover:bg-white/[0.04]'
                      }`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <item.icon className={`w-5 h-5 ${
                        isActive ? 'text-vanguard-400' : 'text-[var(--text-muted)] group-hover:text-vanguard-400/70'
                      }`} aria-hidden="true" />
                      {item.name}
                      {isActive && (
                        <div className="absolute right-2 w-1.5 h-1.5 rounded-full bg-vanguard-400" style={{boxShadow: '0 0 6px rgba(76, 110, 245, 0.6)'}}></div>
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </nav>

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Reserved space for future features */}
      </div>

      <div className="px-4 py-3 border-t border-white/[0.06] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              onClick={openSettings}
              className="p-2 rounded-lg hover:bg-white/[0.04] transition-colors"
              title="Settings"
              aria-label="Open settings"
            >
              <Settings className="w-4 h-4 text-[var(--text-muted)] hover:text-vanguard-400" />
            </button>
          </div>
        </div>
        <div className="text-[10px] text-[var(--text-muted)] font-mono">v0.1.0</div>
      </div>

    </aside>
  </>
  );
}

export default memo(Sidebar);