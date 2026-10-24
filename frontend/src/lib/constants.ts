export interface CategoryConfig {
  name: string;
  iconName: 'CreditCard' | 'Headphones' | 'CupSoda' | 'KeyRound' | 'Briefcase' | 'BookOpen' | 'Umbrella' | 'Package';
}

export const CATEGORIES_WITH_ICONS: CategoryConfig[] = [
  { name: 'ID Cards & Badges', iconName: 'CreditCard' },
  { name: 'Electronics & Tech', iconName: 'Headphones' },
  { name: 'Bottles & Flasks', iconName: 'CupSoda' },
  { name: 'Keys & Tokens', iconName: 'KeyRound' },
  { name: 'Bags & Backpacks', iconName: 'Briefcase' },
  { name: 'Books & Stationery', iconName: 'BookOpen' },
  { name: 'Umbrellas & Apparel', iconName: 'Umbrella' },
  { name: 'Other Belongings', iconName: 'Package' },
];

export const CATEGORIES = CATEGORIES_WITH_ICONS.map((c) => c.name);

export const CAMPUS_LOCATIONS = [
  'AB-1',
  'AB-2',
  'AB-3',
  'AB-4',
  'AB-5',
  'Gate 1',
  'Gate 2',
  'Gate 3',
  'Gate 4',
  'Gate 5',
  'MAHE-Central Library',
  'Marena',
  'HB-4 NW',
  'HB-4 SW',
  'HB-5',
  'HB-1',
  'HB-2',
  'HB-3',
  'Campus Mart',
  'Other',
] as const;