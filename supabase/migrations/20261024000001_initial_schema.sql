-- ==============================================================================
-- Foundly Campus Lost & Found Platform - Supabase Database Schema
-- Migration: 20261024000001_initial_schema.sql
-- Description: Creates profiles, listings, item_responses, RLS policies & Storage
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. PROFILES TABLE
-- Extends auth.users with public profile metadata without exposing private credentials
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    avatar_path TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. LISTINGS TABLE
-- Stores lost and found posts with categorization and status management
CREATE TABLE IF NOT EXISTS public.listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('lost', 'found')),
    title TEXT NOT NULL CHECK (char_length(title) >= 3 AND char_length(title) <= 120),
    description TEXT NOT NULL CHECK (char_length(description) >= 5),
    category TEXT NOT NULL CHECK (category IN (
        'Electronics',
        'ID Cards and Documents',
        'Keys',
        'Bags and Wallets',
        'Clothing',
        'Books and Stationery',
        'Accessories',
        'Water Bottles and Containers',
        'Other'
    )),
    location TEXT NOT NULL,
    specific_spot TEXT,
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    image_path TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. ITEM RESPONSES (CLAIMS & MATCH INQUIRIES)
-- Secure, private communication channel between claimants and post owners
CREATE TABLE IF NOT EXISTS public.item_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES public.listings(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    response_type TEXT NOT NULL CHECK (response_type IN ('claim', 'possible_match')),
    message TEXT NOT NULL CHECK (char_length(message) >= 5),
    contact_info TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'withdrawn')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 5. INDEXES FOR QUERY OPTIMIZATION
CREATE INDEX IF NOT EXISTS idx_listings_type_status_created ON public.listings(type, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_category ON public.listings(category);
CREATE INDEX IF NOT EXISTS idx_listings_location ON public.listings(location);
CREATE INDEX IF NOT EXISTS idx_listings_owner_id ON public.listings(owner_id);
CREATE INDEX IF NOT EXISTS idx_item_responses_listing_id ON public.item_responses(listing_id);
CREATE INDEX IF NOT EXISTS idx_item_responses_sender_id ON public.item_responses(sender_id);

-- 6. AUTOMATIC UPDATED_AT TRIGGER
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_profiles_updated_at ON public.profiles;
CREATE TRIGGER trigger_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trigger_listings_updated_at ON public.listings;
CREATE TRIGGER trigger_listings_updated_at
    BEFORE UPDATE ON public.listings
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trigger_item_responses_updated_at ON public.item_responses;
CREATE TRIGGER trigger_item_responses_updated_at
    BEFORE UPDATE ON public.item_responses
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- 7. AUTO-PROFILE CREATION ON USER SIGNUP
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name, avatar_path)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1), 'Campus Student'),
        NEW.raw_user_meta_data->>'avatar_path'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ==============================================================================
-- 8. ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.item_responses ENABLE ROW LEVEL SECURITY;

-- --- PROFILES POLICIES ---
-- Any authenticated user can read public profile details
DROP POLICY IF EXISTS "Public profiles are viewable by everyone" ON public.profiles;
CREATE POLICY "Public profiles are viewable by everyone"
    ON public.profiles FOR SELECT
    USING (true);

-- Users can only insert their own profile
DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Users can only update their own profile
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- --- LISTINGS POLICIES ---
-- Open & resolved listings are viewable by everyone (public campus directory)
DROP POLICY IF EXISTS "Active and resolved listings are public" ON public.listings;
CREATE POLICY "Active and resolved listings are public"
    ON public.listings FOR SELECT
    USING (
        status IN ('open', 'resolved')
        OR (auth.uid() IS NOT NULL AND auth.uid() = owner_id)
    );

-- Authenticated users can create listings with their own owner_id
DROP POLICY IF EXISTS "Authenticated users can create listings" ON public.listings;
CREATE POLICY "Authenticated users can create listings"
    ON public.listings FOR INSERT
    WITH CHECK (
        auth.role() = 'authenticated'
        AND auth.uid() = owner_id
    );

-- Users can only update listings they own
DROP POLICY IF EXISTS "Users can update own listings" ON public.listings;
CREATE POLICY "Users can update own listings"
    ON public.listings FOR UPDATE
    USING (auth.uid() = owner_id)
    WITH CHECK (auth.uid() = owner_id);

-- Users can only delete or archive listings they own
DROP POLICY IF EXISTS "Users can delete own listings" ON public.listings;
CREATE POLICY "Users can delete own listings"
    ON public.listings FOR DELETE
    USING (auth.uid() = owner_id);

-- --- ITEM RESPONSES POLICIES ---
-- Responses are private: only the sender or the listing owner can view them
DROP POLICY IF EXISTS "Participants can view responses" ON public.item_responses;
CREATE POLICY "Participants can view responses"
    ON public.item_responses FOR SELECT
    USING (
        auth.uid() IS NOT NULL AND (
            sender_id = auth.uid()
            OR auth.uid() = (SELECT owner_id FROM public.listings WHERE id = listing_id)
        )
    );

-- Authenticated users can submit claims, but NOT to their own listings
DROP POLICY IF EXISTS "Users can submit response to others' listings" ON public.item_responses;
CREATE POLICY "Users can submit response to others' listings"
    ON public.item_responses FOR INSERT
    WITH CHECK (
        auth.role() = 'authenticated'
        AND auth.uid() = sender_id
        AND auth.uid() != (SELECT owner_id FROM public.listings WHERE id = listing_id)
    );

-- Listing owners can accept/decline; senders can withdraw
DROP POLICY IF EXISTS "Authorized participants can update response status" ON public.item_responses;
CREATE POLICY "Authorized participants can update response status"
    ON public.item_responses FOR UPDATE
    USING (
        auth.uid() IS NOT NULL AND (
            sender_id = auth.uid()
            OR auth.uid() = (SELECT owner_id FROM public.listings WHERE id = listing_id)
        )
    );

-- ==============================================================================
-- 9. SUPABASE STORAGE BUCKET CONFIGURATION
-- ==============================================================================

-- Create bucket 'item-images' if storage schema is available
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'item-images',
    'item-images',
    true,
    5242880, -- 5 MB limit
    ARRAY['image/jpeg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO UPDATE SET
    public = true,
    file_size_limit = 5242880,
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp'];

-- Storage bucket RLS policies:
-- Public can view/download images
DROP POLICY IF EXISTS "Public can view item images" ON storage.objects;
CREATE POLICY "Public can view item images"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'item-images');

-- Authenticated users can upload to item-images
DROP POLICY IF EXISTS "Authenticated users can upload item images" ON storage.objects;
CREATE POLICY "Authenticated users can upload item images"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'item-images'
        AND auth.role() = 'authenticated'
    );

-- Owners can delete their images
DROP POLICY IF EXISTS "Users can delete own item images" ON storage.objects;
CREATE POLICY "Users can delete own item images"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'item-images'
        AND auth.uid() = owner
    );
