create table if not exists public.items (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(trim(title)) between 1 and 120),
  type text not null check (type in ('lost', 'found')),
  category text not null,
  description text not null check (char_length(trim(description)) between 10 and 2000),
  date_lost_or_found date not null,
  location text not null,
  image_url text,
  contact_email text,
  status text not null default 'open' check (status in ('open', 'resolved')),
  created_at timestamptz not null default now()
);

create index if not exists items_created_at_idx on public.items (created_at desc);
create index if not exists items_status_idx on public.items (status);

alter table public.items enable row level security;

grant select on public.items to anon, authenticated;
revoke insert on public.items from public, anon, authenticated;
grant insert (
  title,
  type,
  category,
  description,
  date_lost_or_found,
  location,
  image_url,
  contact_email
) on public.items to anon, authenticated;

drop policy if exists "Anyone can view reports" on public.items;
create policy "Anyone can view reports"
  on public.items for select
  to anon, authenticated
  using (true);

drop policy if exists "Anyone can submit reports" on public.items;
create policy "Anyone can submit reports"
  on public.items for insert
  to anon, authenticated
  with check (status = 'open');