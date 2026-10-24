import React, { useState, useEffect } from 'react';
import {
  Search,
  PlusCircle,
  ArrowRight,
  ShieldCheck,
  Building2,
  Library,
  CreditCard,
  Headphones,
  CupSoda,
  KeyRound,
  Briefcase,
  BookOpen,
  Umbrella,
  Package,
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { Item } from '../types/database';
import { CATEGORIES_WITH_ICONS } from '../lib/constants';
import { ItemCard } from '../components/ItemCard';

interface HomePageProps {
  onNavigate: (page: string, params?: Record<string, string>) => void;
  onSelectItem: (id: string) => void;
}

const CategoryIconMap = {
  CreditCard,
  Headphones,
  CupSoda,
  KeyRound,
  Briefcase,
  BookOpen,
  Umbrella,
  Package,
};

const itemPhotos = import.meta.glob<string>('../assets/item*.{jpg,jpeg,png,webp}', {
  eager: true,
  import: 'default',
});

const ItemPhoto: React.FC<{ photoNumber: number }> = ({ photoNumber }) => {
  const photoUrl = itemPhotos[`../assets/item${photoNumber}.jpg`]
    ?? itemPhotos[`../assets/item${photoNumber}.jpeg`]
    ?? itemPhotos[`../assets/item${photoNumber}.png`]
    ?? itemPhotos[`../assets/item${photoNumber}.webp`];

  if (!photoUrl) {
    return (
      <div className="h-full min-h-32 bg-campus-sandstone-surface" aria-hidden="true" />
    );
  }

  return <img src={photoUrl} alt="" loading="lazy" className="h-full w-full object-cover" />;
};

export const HomePage: React.FC<HomePageProps> = ({ onNavigate, onSelectItem }) => {
  const [query, setQuery] = useState('');
  const [recentItems, setRecentItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecent();
  }, []);

  const fetchRecent = async () => {
    try {
      const { data, error } = await supabase
        .from('items')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(8);

      if (!error && data) {
        setRecentItems(data as Item[]);
      }
    } catch (err) {
      console.error('Failed to load items', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onNavigate('browse', { search: query });
  };

  return (
    <div className="space-y-14 py-4 sm:py-6">
      {/* 1. Two-Column Hero with Overlapping Listing Photography */}
      <section className="pt-2 sm:pt-5 pb-2">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left Column: Editorial Typography & Actions */}
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-campus-sandstone-border bg-campus-sandstone-surface px-3 py-1.5 text-[10px] font-semibold tracking-[0.14em] uppercase text-campus-espresso-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-campus-terracotta" />
              <span>Lost &amp; found, made simple</span>
            </div>

            <h1 className="font-serif text-5xl sm:text-6xl lg:text-[4.25rem] font-normal tracking-tight text-campus-espresso leading-[1.02]">
              Lost something?
              <span className="mt-1 block italic font-normal text-campus-terracotta">Let's bring it home.</span>
            </h1>

            <p className="text-sm sm:text-base text-campus-espresso-muted max-w-lg leading-relaxed font-sans">
              A thoughtful community exchange for the things that connect us—from a misplaced notebook to the keys you need to get home.
            </p>

            {/* Prominent Search Input */}
            <form onSubmit={handleSearchSubmit} className="pt-1 max-w-xl">
              <div className="flex flex-col sm:flex-row gap-2 rounded-xl border border-campus-sandstone-border bg-white p-1.5 shadow-warm focus-within:border-campus-terracotta/60 focus-within:ring-2 focus-within:ring-campus-terracotta/10">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-3 w-4 h-4 text-campus-espresso-subtle" />
                  <input
                    type="text"
                    aria-label="Search items"
                    placeholder="Search by item, place, or keyword..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full rounded-lg bg-transparent pl-10 pr-3 py-2.5 text-sm text-campus-espresso placeholder:text-campus-espresso-subtle focus:outline-none"
                  />
                </div>
                <button
                  type="submit"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-campus-terracotta hover:bg-campus-terracotta-hover px-5 py-2.5 text-sm font-semibold text-white dark:bg-campus-terracotta-light dark:text-campus-terracotta-text dark:hover:bg-campus-terracotta-light transition-colors shadow-warm"
                >
                  <Search className="h-4 w-4" />
                  Search
                </button>
              </div>
            </form>

            {/* Lost / Found Direct Action Buttons */}
            <div className="pt-1 flex flex-wrap items-center gap-2.5 text-xs font-sans">
              <button
                onClick={() => onNavigate('report', { type: 'lost' })}
                className="inline-flex items-center gap-2 rounded-full border border-campus-terracotta px-4 py-2.5 font-semibold text-white bg-campus-terracotta hover:bg-campus-terracotta-hover dark:border-campus-terracotta-border dark:bg-campus-terracotta-light dark:text-campus-terracotta-text dark:hover:bg-campus-terracotta-light transition-all shadow-warm hover:shadow-warm-md"
              >
                <PlusCircle className="h-3.5 w-3.5" />
                I lost something
              </button>
              <button
                onClick={() => onNavigate('report', { type: 'found' })}
                className="inline-flex items-center gap-2 rounded-full border border-campus-turmeric px-4 py-2.5 font-semibold text-campus-espresso bg-campus-turmeric hover:bg-campus-turmeric-hover dark:border-campus-turmeric-border dark:bg-campus-turmeric-light dark:text-campus-turmeric-text dark:hover:bg-campus-turmeric-light transition-all shadow-warm hover:shadow-warm-md"
              >
                <PlusCircle className="h-3.5 w-3.5" />
                I found something
              </button>
              <button
                onClick={() => onNavigate('browse')}
                className="inline-flex items-center gap-2 rounded-full border border-campus-sandstone-border bg-white px-4 py-2.5 font-semibold text-campus-espresso hover:border-campus-espresso/30 hover:bg-campus-sandstone-surface transition-all"
              >
                Browse listings <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="lg:col-span-6 relative isolate mx-auto w-full max-w-[540px] aspect-[1.48/1] sm:-translate-x-11 lg:translate-x-0">
            <div className="absolute right-[2%] top-0 h-[73%] w-[76%] overflow-hidden rounded-2xl border border-campus-sandstone-border bg-campus-sandstone-surface shadow-warm-md">
              <ItemPhoto photoNumber={1} />
            </div>
            <div className="absolute bottom-[3%] left-0 z-10 h-[48%] w-[53%] overflow-hidden rounded-2xl border-4 border-campus-ivory bg-campus-sandstone-surface shadow-warm-md">
              <ItemPhoto photoNumber={2} />
            </div>
            <div className="absolute bottom-0 right-[4%] h-[37%] w-[35%] overflow-hidden rounded-2xl border-4 border-campus-ivory bg-campus-sandstone-surface shadow-warm">
              <ItemPhoto photoNumber={3} />
            </div>
          </div>
        </div>
      </section>

      {/* 2. Restrained Feature Strip */}
      <section className="bg-campus-sandstone-surface rounded-lg border border-campus-sandstone-border p-4 sm:p-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 divide-y md:divide-y-0 md:divide-x divide-campus-sandstone-border">
          <div className="flex items-start gap-3 md:pr-4">
            <Building2 className="w-4 h-4 text-campus-terracotta shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-semibold text-campus-espresso">Share a useful description</h4>
              <p className="text-[11px] text-campus-espresso-muted mt-0.5">A color, brand, or identifying detail can help an item find its owner.</p>
            </div>
          </div>

          <div className="flex items-start gap-3 pt-3 md:pt-0 md:px-4">
            <Library className="w-4 h-4 text-campus-turmeric shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-semibold text-campus-espresso">Add a clear photo</h4>
              <p className="text-[11px] text-campus-espresso-muted mt-0.5">A simple photo makes listings easier to recognize at a glance.</p>
            </div>
          </div>

          <div className="flex items-start gap-3 pt-3 md:pt-0 md:pl-4">
            <ShieldCheck className="w-4 h-4 text-campus-terracotta shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-semibold text-campus-espresso">Arrange a safe handover</h4>
              <p className="text-[11px] text-campus-espresso-muted mt-0.5">Coordinate directly with the person who posted the lost or found item.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Icon-Based Category Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-serif text-2xl text-campus-espresso font-normal">Browse by category</h2>
            <p className="text-xs text-campus-espresso-muted mt-0.5 font-sans">Start with the kind of thing you are looking for</p>
          </div>
          <button
            onClick={() => onNavigate('browse')}
            className="text-xs font-semibold text-campus-terracotta hover:underline inline-flex items-center gap-1 font-sans"
          >
            <span>View directory</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {CATEGORIES_WITH_ICONS.map((cat) => {
            const Icon = CategoryIconMap[cat.iconName];
            return (
              <button
                key={cat.name}
                onClick={() => onNavigate('browse', { category: cat.name })}
                className="p-3.5 text-left bg-white rounded border border-campus-sandstone-border hover:border-campus-terracotta/50 hover:bg-campus-sandstone-surface transition-all text-xs font-sans group flex items-center gap-3 shadow-2xs"
              >
                <div className="w-8 h-8 rounded bg-campus-sandstone/60 group-hover:bg-campus-terracotta-light flex items-center justify-center shrink-0 transition-colors">
                  <Icon className="w-4 h-4 text-campus-espresso group-hover:text-campus-terracotta transition-colors" />
                </div>
                <span className="font-medium text-campus-espresso group-hover:text-campus-terracotta truncate">
                  {cat.name}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* 4. Recently Reported Cards */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-serif text-2xl text-campus-espresso font-normal">Recently Reported</h2>
            <p className="text-xs text-campus-espresso-muted mt-0.5 font-sans">The latest lost and found notices from the community</p>
          </div>
          <button
            onClick={() => onNavigate('browse')}
            className="text-xs font-semibold text-campus-terracotta hover:underline inline-flex items-center gap-1 font-sans"
          >
            <span>All records</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="bg-white rounded border border-campus-sandstone-border p-3 h-64 animate-pulse">
                <div className="bg-campus-sandstone h-36 rounded mb-3" />
                <div className="h-4 bg-campus-sandstone rounded w-2/3 mb-2" />
                <div className="h-3 bg-campus-sandstone rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : recentItems.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recentItems.map((item) => (
              <ItemCard key={item.id} item={item} onClick={() => onSelectItem(item.id)} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded border border-dashed border-campus-sandstone-border">
            <p className="text-xs text-campus-espresso-muted font-sans">No listings yet. Be the first to post one.</p>
          </div>
        )}
      </section>
    </div>
  );
};