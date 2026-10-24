export const isUsableItemImage = (imageUrl: string | null): imageUrl is string =>
  Boolean(imageUrl?.trim() && !/^https?:\/\/images\.unsplash\.com\//i.test(imageUrl.trim()));
