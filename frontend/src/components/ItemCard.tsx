import React, { useState } from 'react';
import { Calendar, MapPin, PackageOpen } from 'lucide-react';
import { Item } from '../types/database';
import { Badge } from './Badge';
import { isUsableItemImage } from '../lib/itemImages';

interface ItemCardProps {
  item: Item;
  onClick: () => void;
}

export const ItemCard: React.FC<ItemCardProps> = ({ item, onClick }) => {
  const [imgError, setImgError] = useState(false);
  const imageUrl = isUsableItemImage(item.image_url) ? item.image_url : null;

  return (
    <article
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onClick();
        }
      }}
      className="group bg-white rounded-xl border border-campus-sandstone-border hover:-translate-y-0.5 hover:border-campus-terracotta/40 transition-all duration-200 overflow-hidden cursor-pointer flex flex-col h-full shadow-warm hover:shadow-warm-md focus-visible:outline-campus-terracotta"
    >
      <div className="relative aspect-[4/3] w-full bg-campus-sandstone-surface overflow-hidden border-b border-campus-sandstone-border/70">
        {imageUrl && !imgError ? (
          <img
            src={imageUrl}
            alt={item.title}
            onError={() => setImgError(true)}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-campus-espresso-subtle p-4 text-center bg-campus-sandstone/40">
            <PackageOpen className="w-7 h-7 stroke-[1.25] text-campus-espresso-muted mb-1" />
            <span className="text-[11px] font-sans text-campus-espresso-muted">Photo unavailable</span>
          </div>
        )}
        <div className="absolute top-2.5 left-2.5 flex gap-1.5">
          <Badge variant={item.type}>{item.type}</Badge>
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between text-[11px] text-campus-espresso-muted mb-1 font-sans">
            <span className="font-semibold text-campus-terracotta tracking-wide">{item.category}</span>
            <span>{new Date(item.created_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}</span>
          </div>
          <h3 className="font-serif text-[17px] text-campus-espresso font-normal leading-snug line-clamp-1 group-hover:text-campus-terracotta transition-colors">
            {item.title}
          </h3>
          <p className="text-xs text-campus-espresso-muted mt-1.5 line-clamp-2 leading-relaxed">
            {item.description}
          </p>
        </div>

        <div className="mt-4 pt-3 border-t border-campus-sandstone-border/60 flex items-center justify-between text-[11px] text-campus-espresso-muted">
          <div className="flex items-center gap-1.5 truncate mr-2">
            <MapPin className="w-3.5 h-3.5 text-campus-terracotta shrink-0" />
            <span className="truncate">{item.location}</span>
          </div>
          <div className="flex items-center gap-1 shrink-0 text-campus-espresso-subtle">
            <Calendar className="w-3 h-3" />
            <span>{item.date_lost_or_found}</span>
          </div>
        </div>
      </div>
    </article>
  );
};