export type ItemType = 'lost' | 'found';
export type ItemStatus = 'open' | 'resolved';

export interface Item {
  id: string;
  title: string;
  type: ItemType;
  category: string;
  description: string;
  date_lost_or_found: string;
  location: string;
  image_url: string | null;
  contact_email: string | null;
  status: ItemStatus;
  created_at: string;
}

export type ItemFormData = Omit<Item, 'id' | 'created_at' | 'status'>;