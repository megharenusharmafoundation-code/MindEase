begin;

create extension if not exists pgcrypto;

create or replace function public.set_user_profile_static_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.user_profile_static (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  age integer check (age between 1 and 120),
  gender text check (gender in ('male', 'female', 'other', 'prefer-not')),
  height numeric(5,2) check (height between 50 and 250),
  weight numeric(5,2) check (weight between 20 and 300),
  diagnosed_bp text check (diagnosed_bp in ('yes', 'no')),
  diagnosed_diabetes text check (diagnosed_diabetes in ('yes', 'no')),
  thyroid_disorder text check (thyroid_disorder in ('yes', 'no')),
  heart_cholesterol text check (heart_cholesterol in ('yes', 'no')),
  chronic_illness text,
  family_bp text check (family_bp in ('yes', 'no')),
  family_diabetes text check (family_diabetes in ('yes', 'no')),
  family_heart_disease text check (family_heart_disease in ('yes', 'no')),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_user_profile_static_user_id
on public.user_profile_static (user_id);

drop trigger if exists trg_user_profile_static_updated_at on public.user_profile_static;
create trigger trg_user_profile_static_updated_at
before update on public.user_profile_static
for each row
execute function public.set_user_profile_static_updated_at();

alter table public.user_profile_static enable row level security;

drop policy if exists "user_profile_static_select_own" on public.user_profile_static;
create policy "user_profile_static_select_own"
on public.user_profile_static
for select
using (auth.uid() = user_id);

drop policy if exists "user_profile_static_insert_own" on public.user_profile_static;
create policy "user_profile_static_insert_own"
on public.user_profile_static
for insert
with check (auth.uid() = user_id);

drop policy if exists "user_profile_static_update_own" on public.user_profile_static;
create policy "user_profile_static_update_own"
on public.user_profile_static
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "user_profile_static_delete_own" on public.user_profile_static;
create policy "user_profile_static_delete_own"
on public.user_profile_static
for delete
using (auth.uid() = user_id);

commit;
