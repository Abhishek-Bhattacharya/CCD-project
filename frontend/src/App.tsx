import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { HomePage } from './pages/Homepage';
import { BrowsePage } from './pages/BrowsePage';
import { ItemDetailPage } from './pages/ItemDetailpage';
import { ReportItemPage } from './pages/ReportItemPage';
import { ItemType } from './types/database';

type AppPage = 'home' | 'browse' | 'report' | 'item';

interface AppRoute {
  foundly: true;
  page: AppPage;
  params: Record<string, string>;
  itemId?: string;
}

const readAppRoute = (value: unknown): AppRoute | null => {
  if (!value || typeof value !== 'object') return null;
  const route = value as Partial<AppRoute>;
  if (
    route.foundly !== true ||
    !route.page ||
    !['home', 'browse', 'report', 'item'].includes(route.page)
  ) {
    return null;
  }

  const params =
    route.params && typeof route.params === 'object'
      ? Object.fromEntries(
          Object.entries(route.params).filter(
            (entry): entry is [string, string] => typeof entry[1] === 'string'
          )
        )
      : {};

  if (route.page === 'item' && typeof route.itemId !== 'string') return null;

  return {
    foundly: true,
    page: route.page,
    params,
    ...(route.page === 'item' ? { itemId: route.itemId } : {}),
  };
};

export const App: React.FC = () => {
  const [isDark, setIsDark] = useState(() => {
    const savedTheme = localStorage.getItem('foundly-theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const [route, setRoute] = useState<AppRoute>(
    () => readAppRoute(window.history.state) ?? {
      foundly: true,
      page: 'home',
      params: {},
    }
  );

  useEffect(() => {
    if (!readAppRoute(window.history.state)) {
      window.history.replaceState(route, '', window.location.href);
    }

    const handlePopState = (event: PopStateEvent) => {
      const previousRoute = readAppRoute(event.state);
      setRoute(previousRoute ?? { foundly: true, page: 'home', params: {} });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
  }, [isDark]);

  const handleToggleTheme = () => {
    setIsDark((current) => {
      const next = !current;
      localStorage.setItem('foundly-theme', next ? 'dark' : 'light');
      return next;
    });
  };

  const handleNavigate = (page: string, params: Record<string, string> = {}) => {
    const nextRoute: AppRoute = {
      foundly: true,
      page: page as AppPage,
      params,
    };
    window.history.pushState(nextRoute, '', window.location.href);
    setRoute(nextRoute);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectItem = (id: string) => {
    const nextRoute: AppRoute = {
      foundly: true,
      page: 'item',
      params: {},
      itemId: id,
    };
    window.history.pushState(nextRoute, '', window.location.href);
    setRoute(nextRoute);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-campus-ivory text-campus-espresso">
      <Navbar
        currentPage={route.page}
        onNavigate={handleNavigate}
        isDark={isDark}
        onToggleTheme={handleToggleTheme}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        {route.page === 'home' && (
          <HomePage onNavigate={handleNavigate} onSelectItem={handleSelectItem} />
        )}

        {route.page === 'browse' && (
          <BrowsePage
            initialSearch={route.params.search || ''}
            initialCategory={route.params.category || ''}
            onSelectItem={handleSelectItem}
          />
        )}

        {route.page === 'report' && (
          <ReportItemPage
            initialType={(route.params.type as ItemType) || 'lost'}
            onSuccess={(id) => handleSelectItem(id)}
          />
        )}

        {route.page === 'item' && route.itemId && (
          <ItemDetailPage
            itemId={route.itemId}
            onBack={() => window.history.back()}
          />
        )}
      </main>

      <Footer />
    </div>
  );
};