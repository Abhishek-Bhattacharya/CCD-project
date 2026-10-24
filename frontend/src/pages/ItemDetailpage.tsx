import React, { useEffect, useState } from 'react';
import { ArrowLeft, Calendar, MapPin, Mail, AlertCircle, PackageOpen } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { Item } from '../types/database';
import { Badge } from '../components/Badge';
import { ContactModal } from '../components/ContactModal';
import { isUsableItemImage } from '../lib/itemImages';

interface ItemDetailPageProps {
  itemId: string;
  onBack: () => void;
}

export const ItemDetailPage: React.FC<ItemDetailPageProps> = ({ itemId, onBack }) => {
  const [item, setItem] = useState<Item | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const fetchItem = async () => {
      try {
        const { data, error } = await supabase
          .from('items')
          .select('*')
          .eq('id', itemId)
          .single();

        if (error || !data) {
          setError('Record not found.');
        } else {
          setItem(data as Item);
        }
      } catch (err) {
        setError('Failed to load item.');
      } finally {
        setLoading(false);
      }
    };

    fetchItem();
  }, [itemId]);

  if (loading) {
    return (
      <div className="py-20 flex justify-center items-center">
        <div className="w-6 h-6 border-2 border-campus-terracotta border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="py-16 text-center">
        <AlertCircle className="w-10 h-10 text-campus-terracotta mx-auto mb-2" />
        <h2 className="font-serif text-xl text-campus-espresso">{error}</h2>
        <button
          onClick={onBack}
          className="mt-4 px-3 py-1.5 bg-white border border-campus-sandstone-border rounded text-xs text-campus-espresso"
        >
          Return to Directory
        </button>
      </div>
    );
  }

  const imageUrl = isUsableItemImage(item.image_url) ? item.image_url : null;

  return (
    <div className="max-w-3xl mx-auto py-4">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-xs text-campus-espresso-muted hover:text-campus-espresso mb-4 transition-colors font-sans"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to listings</span>
      </button>

      <div className="bg-white rounded border border-campus-sandstone-border overflow-hidden shadow-warm">
        <div className="w-full bg-campus-sandstone-surface border-b border-campus-sandstone-border flex items-center justify-center relative">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={item.title}
              className="max-h-96 w-full object-contain"
            />
          ) : (
            <div className="py-16 text-center text-campus-espresso-subtle">
              <PackageOpen className="w-10 h-10 mx-auto stroke-[1.25] mb-2" />
              <p className="text-xs font-sans">Photo unavailable.</p>
            </div>
          )}
          <div className="absolute top-3 left-3 flex gap-1.5">
            <Badge variant={item.type}>{item.type}</Badge>
            <Badge variant={item.status}>{item.status}</Badge>
          </div>
        </div>

        <div className="p-6 sm:p-8 space-y-6">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-wider text-campus-terracotta">
              {item.category}
            </span>
            <h1 className="font-serif text-2xl sm:text-3xl text-campus-espresso font-normal mt-1">
              {item.title}
            </h1>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 py-3 border-y border-campus-sandstone-border/60 text-xs font-sans">
            <div className="flex items-center gap-2 text-campus-espresso-muted">
              <MapPin className="w-4 h-4 text-campus-terracotta shrink-0" />
              <span className="text-campus-espresso font-semibold">Location:</span>
              <span>{item.location}</span>
            </div>
            <div className="flex items-center gap-2 text-campus-espresso-muted">
              <Calendar className="w-4 h-4 text-campus-terracotta shrink-0" />
              <span className="text-campus-espresso font-semibold">Date reported:</span>
              <span>{item.date_lost_or_found}</span>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-campus-espresso font-sans mb-1.5">
              Description & Identifying Marks
            </h3>
            <p className="text-sm text-campus-espresso-muted leading-relaxed font-sans whitespace-pre-wrap">
              {item.description}
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={() => setIsModalOpen(true)}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded bg-campus-terracotta hover:bg-campus-terracotta-hover text-white dark:bg-campus-terracotta-light dark:text-campus-terracotta-text dark:hover:bg-campus-terracotta-light text-xs font-medium transition-colors shadow-2xs"
            >
              <Mail className="w-3.5 h-3.5" />
              <span>Contact {item.type === 'lost' ? 'Owner' : 'Finder'}</span>
            </button>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <ContactModal
          email={item.contact_email}
          itemTitle={item.title}
          itemType={item.type}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
};