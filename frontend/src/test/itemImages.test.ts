import { describe, expect, it } from 'vitest';
import { isUsableItemImage } from '../lib/itemImages';

describe('Foundly item photos', () => {
  it('uses uploaded and local item photos', () => {
    expect(isUsableItemImage('/assets/campus-item.jpg')).toBe(true);
    expect(isUsableItemImage('https://project.supabase.co/storage/v1/item-photo.jpg')).toBe(true);
  });

  it('uses the placeholder for missing or Unsplash stock photos', () => {
    expect(isUsableItemImage(null)).toBe(false);
    expect(isUsableItemImage('https://images.unsplash.com/photo-123')).toBe(false);
  });
});
