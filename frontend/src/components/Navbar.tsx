import React from 'react';
import { Compass, Moon, PlusCircle, Search, Sun } from 'lucide-react';

interface NavbarProps {
  currentPage: string;
  onNavigate: (page: string, params?: Record<string, string>) => void;
  isDark: boolean;
  onToggleTheme: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentPage,
  onNavigate,
  isDark,
  onToggleTheme,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-campus-ivory/95 backdrop-blur-sm border-b border-campus-sandstone-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <button
          onClick={() => onNavigate('home')}
          className="flex items-center gap-2.5 text-left focus:outline-none group"
        >
          <div className="w-7 h-7 rounded bg-campus-terracotta flex items-center justify-center text-white shadow-2xs">
            <Search className="w-3.5 h-3.5 stroke-[2.5]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-xl tracking-tight text-campus-espresso">
              Found<span className="italic text-campus-terracotta">ly</span>
            </span>
            <span className="hidden sm:inline-block text-[10px] font-sans font-semibold tracking-wider uppercase text-campus-espresso-subtle">
              LOST &amp; FOUND
            </span>
          </div>
        </button>

        <nav className="flex items-center gap-1.5 sm:gap-2">
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            aria-pressed={isDark}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-campus-sandstone-border text-campus-espresso-muted hover:bg-campus-sandstone/60 hover:text-campus-espresso transition-colors"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={() => onNavigate('browse')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-2 rounded-full text-xs font-medium transition-colors ${
              currentPage === 'browse'
                ? 'bg-campus-sandstone text-campus-espresso font-semibold'
                : 'text-campus-espresso hover:bg-campus-sandstone/50'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Directory</span>
          </button>

          <button
            onClick={() => onNavigate('report')}
            className="flex items-center gap-1.5 px-3 sm:px-3.5 py-2 rounded-full bg-campus-terracotta hover:bg-campus-terracotta-hover text-white dark:bg-campus-terracotta-light dark:text-campus-terracotta-text dark:hover:bg-campus-terracotta-light text-xs font-medium transition-colors shadow-warm"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Report Item</span>
          </button>
        </nav>
      </div>
    </header>
  );
};