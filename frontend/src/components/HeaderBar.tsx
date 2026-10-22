import React from 'react';
import {
  Bell,
  BookmarkCheck,
  Link2,
  Moon,
  PackageCheck,
  Search,
  Snowflake,
  Sun,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useLotCart } from '../context/LotCartContext';

export type ActiveTab = 'search' | 'urls' | 'watchlist' | 'alerts';

interface HeaderBarProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  watchlistCount: number;
  enginesOnline: number;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  activeTab,
  onSelectTab,
  watchlistCount,
  enginesOnline,
}) => {
  const { theme, toggleTheme } = useTheme();
  const { entries, setOpen } = useLotCart();

  const totalUnits = entries.reduce((acc, item) => acc + item.quantity, 0);

  const navItems: Array<{
    id: ActiveTab;
    label: string;
    icon: React.ReactNode;
    badge?: number;
  }> = [
    {
      id: 'search',
      label: 'Comparador Real',
      icon: <Search className="w-4 h-4" />,
    },
    {
      id: 'urls',
      label: 'URL & Dorks Web',
      icon: <Link2 className="w-4 h-4" />,
    },
    {
      id: 'watchlist',
      label: 'Watchlist',
      icon: <BookmarkCheck className="w-4 h-4" />,
      badge: watchlistCount > 0 ? watchlistCount : undefined,
    },
    {
      id: 'alerts',
      label: 'WhatsApp & Webhooks',
      icon: <Bell className="w-4 h-4" />,
    },
  ];

  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-white/85 dark:bg-[#070B14]/85 border-b border-slate-200/80 dark:border-slate-800/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand Identity */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-slate-900 dark:bg-cyan-500/15 border border-slate-800 dark:border-cyan-400/30 flex items-center justify-center text-cyan-400 shadow-xs">
            <Snowflake className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold tracking-tight text-sm sm:text-base text-slate-900 dark:text-slate-100">
                ICEBERG
              </span>
              <span className="text-[10px] font-medium uppercase tracking-widest px-1.5 py-0.5 rounded bg-sky-100 text-sky-800 dark:bg-cyan-500/15 dark:text-cyan-300 border border-sky-200/70 dark:border-cyan-400/20">
                Price Radar
              </span>
            </div>
            <p className="hidden md:block text-[11px] text-slate-500 dark:text-slate-400">
              Scraping Real Multi-Loja · PIX, Parcelado & Arbitragem
            </p>
          </div>
        </div>

        {/* Center Navigation */}
        <nav className="flex items-center gap-1 overflow-x-auto py-1">
          {navItems.map((item) => {
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap transition-all cursor-pointer ${
                  active
                    ? 'bg-slate-900 text-white dark:bg-cyan-500/15 dark:text-cyan-300 dark:border dark:border-cyan-400/30'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-100 dark:hover:bg-slate-800/60'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
                {item.badge !== undefined && (
                  <span className="num-mono text-[11px] px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-700 dark:text-cyan-300">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Actions: Live Engine Status, Lote CSV Drawer & Dual Cold Theme Switch */}
        <div className="flex items-center gap-2">
          <div
            title="Motores reais de scraping online (Zero Mock Data)"
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
            <span className="num-mono">{enginesOnline} Scrapers Ativos</span>
          </div>

          <button
            onClick={() => setOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white transition-colors cursor-pointer shadow-xs"
          >
            <PackageCheck className="w-4 h-4" />
            <span className="hidden sm:inline">Lote & CSV</span>
            <span className="num-mono px-1.5 py-0.2 rounded bg-white/20 text-[11px]">
              {totalUnits}
            </span>
          </button>

          <button
            onClick={toggleTheme}
            title={
              theme === 'obsidian'
                ? 'Alternar para Modo Claro Ártico'
                : 'Alternar para Modo Escuro Obsidiana'
            }
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:border-sky-400 dark:hover:border-cyan-400/50 transition-colors cursor-pointer"
          >
            {theme === 'obsidian' ? (
              <Sun className="w-4 h-4 text-cyan-300" />
            ) : (
              <Moon className="w-4 h-4 text-slate-700" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
