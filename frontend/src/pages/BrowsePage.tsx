import React, { useState, useEffect, useMemo } from 'react';
import { Search, RotateCcw, PackageSearch } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { Item, ItemType } from '../types/database';
import { CATEGORIES, CAMPUS_LOCATIONS } from '../lib/constants';
import { ItemCard } from '../components/ItemCard';

interface BrowsePageProps {
  initialSearch?: string;
  initialCategory?: string;
  onSelectItem: (id: string) => void;
}

export const BrowsePage: React.FC<BrowsePageProps> = ({
  initialSearch = '',
  initialCategory = '',
  onSelectItem,
}) => {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  const [typeFilter, setTypeFilter] = useState<'all' | ItemType>('all');
  const [categoryFilter, setCategoryFilter] = useState(initialCategory);
  const [locationFilter, setLocationFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState(initialSearch);

  useEffect(() => {
    fetchItems();
  }, [typeFilter, categoryFilter, locationFilter]);

  const fetchItems = async () => {
    setLoading(true);
    try {
      let query = supabase
        .from('items')
        .select('*')
        .order('created_at', { ascending: false });

      if (typeFilter !== 'all') {
        query = query.eq('type', typeFilter);
      }
      if (categoryFilter) {
        query = query.eq('category', categoryFilter);
      }
      if (locationFilter) {
        query = query.eq('location', locationFilter);
      }

      const { data, error } = await query;
      if (!error && data) {
        setItems(data as Item[]);
      }
    } catch (err) {
      console.error('Error fetching directory items', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = useMemo(() => {
    if (!searchTerm.trim()) return items;
    const term = searchTerm.toLowerCase();
    return items.filter(
      (item) =>
        item.title.toLowerCase().includes(term) ||
        item.description.toLowerCase().includes(term) ||
        item.location.toLowerCase().includes(term)
    );
  }, [items, searchTerm]);

  const resetFilters = () => {
    setTypeFilter('all');
    setCategoryFilter('');
    setLocationFilter('');
    setSearchTerm('');
  };

  return (
    <div className="space-y-7 py-3 sm:py-5">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-campus-sandstone-border pb-5">
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-campus-terracotta">Community listings</span>
          <h1 className="mt-1 font-serif text-3xl sm:text-4xl text-campus-espresso font-normal">Browse items</h1>
          <p className="text-xs text-campus-espresso-muted mt-1.5 font-sans">
            Showing {filteredItems.length} active listing{filteredItems.length === 1 ? '' : 's'}
          </p>
        </div>

        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-campus-espresso-subtle" />
          <input
            type="text"
            placeholder="Filter keyword..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white border border-campus-sandstone-border text-xs text-campus-espresso shadow-warm focus:outline-none focus:ring-2 focus:ring-campus-terracotta/20 focus:border-campus-terracotta"
          />
        </div>
      </div>

      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-campus-sandstone-border space-y-4 shadow-warm">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="inline-flex rounded-full border border-campus-sandstone-border bg-campus-ivory p-1">
            {(['all', 'lost', 'found'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setTypeFilter(tab)}
                className={`px-3.5 py-1.5 rounded-full text-xs capitalize transition-colors ${
                  typeFilter === tab
                    ? 'bg-campus-terracotta text-white dark:bg-campus-terracotta-light dark:text-campus-terracotta-text font-semibold shadow-2xs'
                    : 'text-campus-espresso-muted hover:text-campus-espresso'
                }`}
              >
                {tab === 'all' ? 'All Items' : tab}
              </button>
            ))}
          </div>

          {(typeFilter !== 'all' || categoryFilter || locationFilter || searchTerm) && (
            <button
              onClick={resetFilters}
              className="text-xs text-campus-terracotta hover:underline inline-flex items-center gap-1 font-medium"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset filters</span>
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-campus-sandstone-border/60">
          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1">
              Category
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full p-2 text-xs rounded bg-campus-ivory border border-campus-sandstone-border text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta"
            >
              <option value="">All Categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-campus-espresso-muted uppercase tracking-wider mb-1">
              Location
            </label>
            <select
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className="w-full p-2 text-xs rounded bg-campus-ivory border border-campus-sandstone-border text-campus-espresso focus:outline-none focus:ring-1 focus:ring-campus-terracotta"
            >
              <option value="">All Locations</option>
              {CAMPUS_LOCATIONS.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>
        </div>
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
      ) : filteredItems.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {filteredItems.map((item) => (
            <ItemCard key={item.id} item={item} onClick={() => onSelectItem(item.id)} />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded border border-dashed border-campus-sandstone-border">
          <PackageSearch className="w-8 h-8 text-campus-espresso-subtle mx-auto mb-2" />
          <h3 className="font-serif text-lg text-campus-espresso">No records matching your search</h3>
          <p className="text-xs text-campus-espresso-muted mt-1 font-sans">
            Adjust your keyword or reset filters to view all entries.
          </p>
        </div>
      )}
    </div>
  );
};