begin;

create extension if not exists pgcrypto;

create or replace function public.set_health_profile_updated_at()
returns trigger
language plpgsql
as $$
begin
  new."updatedAt" = timezone('utc', now());
  return new;
end;
$$;

create or replace function public.set_users_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  full_name text,
  role text not null default 'user' check (role in ('user', 'admin')),
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

drop trigger if exists trg_users_updated_at on public.users;
create trigger trg_users_updated_at
before update on public.users
for each row
execute function public.set_users_updated_at();

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  insert into public.users (
    id,
    email,
    full_name,
    role,
    is_active
  )
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    'user',
    true
  )
  on conflict (id) do update
  set
    email = excluded.email,
    full_name = case
      when excluded.full_name <> '' then excluded.full_name
      else public.users.full_name
    end,
    updated_at = timezone('utc', now());

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_auth_user();

insert into public.users (id, email, full_name, role, is_active)
select
  au.id,
  au.email,
  nullif(au.raw_user_meta_data ->> 'full_name', ''),
  'user',
  true
from auth.users au
on conflict (id) do update
set
  email = excluded.email,
  full_name = coalesce(excluded.full_name, public.users.full_name),
  updated_at = timezone('utc', now());

create table if not exists public.health_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  user_email text,
  age integer check (age between 1 and 120),
  gender text check (gender in ('male', 'female', 'other', 'prefer-not')),
  height numeric(5,2) check (height between 50 and 250),
  weight numeric(5,2) check (weight between 20 and 300),
  diagnosed_bp text check (diagnosed_bp in ('yes', 'no')),
  diagnosed_diabetes text check (diagnosed_diabetes in ('yes', 'no')),
  thyroid_disorder text check (thyroid_disorder in ('yes', 'no')),
  heart_cholesterol text check (heart_cholesterol in ('yes', 'no')),
  chronic_illness text,
  screen_time numeric(4,1) check (screen_time between 0 and 24),
  sleep_duration numeric(4,1) check (sleep_duration between 0 and 24),
  feel_rested text check (feel_rested in ('yes', 'no')),
  water_intake numeric(4,1) check (water_intake between 0 and 20),
  tea_coffee integer check (tea_coffee between 0 and 10),
  energy_drinks text check (energy_drinks in ('yes', 'no')),
  sugar_items integer check (sugar_items between 0 and 20),
  soft_drinks text check (soft_drinks in ('Never', 'Sometimes', 'Daily')),
  junk_food text check (junk_food in ('Rarely', 'Sometimes', 'Frequently')),
  alcohol text check (alcohol in ('Never', 'Occasionally', 'Frequently')),
  smoking text check (smoking in ('Never', 'Occasionally', 'Daily')),
  exercise_days integer check (exercise_days between 0 and 7),
  exercise_duration integer check (exercise_duration between 0 and 480),
  activity_type text check (activity_type in ('Walking', 'Gym', 'Yoga', 'None', 'Other')),
  stress_frequency text check (stress_frequency in ('Rarely', 'Sometimes', 'Often')),
  social_interactions integer check (social_interactions between 0 and 50),
  emotional_support text check (emotional_support in ('yes', 'no')),
  family_bp text check (family_bp in ('yes', 'no')),
  family_diabetes text check (family_diabetes in ('yes', 'no')),
  family_heart_disease text check (family_heart_disease in ('yes', 'no')),
  stress_score integer check (stress_score between 0 and 100),
  stress_level text check (stress_level in ('Low', 'Moderate', 'High', 'Healthy', 'Unhealthy')),
  bp_risk text check (bp_risk in ('Low', 'Moderate', 'High')),
  diabetes_risk text check (diabetes_risk in ('Low', 'Moderate', 'High')),
  "updatedAt" timestamptz not null default timezone('utc', now()),
  last_updated timestamptz,
  created_at timestamptz not null default timezone('utc', now())
);

drop trigger if exists trg_health_profiles_updated_at on public.health_profiles;
create trigger trg_health_profiles_updated_at
before update on public.health_profiles
for each row
execute function public.set_health_profile_updated_at();

create table if not exists public.daily_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  log_date date not null,
  stress_score integer not null check (stress_score between 0 and 100),
  sleep_hours numeric(4,1) check (sleep_hours between 0 and 24),
  water_intake_l numeric(4,1) check (water_intake_l between 0 and 20),
  bmi numeric(5,2) check (bmi between 0 and 100),
  exercise_days integer check (exercise_days between 0 and 7),
  saved_at timestamptz not null default timezone('utc', now()),
  constraint daily_logs_user_date_key unique (user_id, log_date)
);

create table if not exists public.stress_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  stress_level integer not null check (stress_level between 0 and 100),
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.wellness_goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  goal_text text not null,
  completed boolean not null default true,
  saved_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.gratitude_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  item_1 text,
  item_2 text,
  item_3 text,
  item_4 text,
  item_5 text,
  happy_moment text,
  entry_date date not null,
  saved_at timestamptz not null default timezone('utc', now()),
  constraint gratitude_entries_user_date_key unique (user_id, entry_date)
);

create index if not exists idx_daily_logs_user_date on public.daily_logs (user_id, log_date desc);
create index if not exists idx_stress_entries_user_created_at on public.stress_entries (user_id, created_at desc);
create index if not exists idx_wellness_goals_user_saved_at on public.wellness_goals (user_id, saved_at desc);
create index if not exists idx_gratitude_entries_user_date on public.gratitude_entries (user_id, entry_date desc);

alter table public.health_profiles enable row level security;
alter table public.daily_logs enable row level security;
alter table public.stress_entries enable row level security;
alter table public.wellness_goals enable row level security;
alter table public.gratitude_entries enable row level security;
alter table public.users enable row level security;

drop policy if exists "users_select_own" on public.users;
create policy "users_select_own"
on public.users
for select
using (auth.uid() = id);

drop policy if exists "users_update_own" on public.users;
create policy "users_update_own"
on public.users
for update
using (auth.uid() = id)
with check (auth.uid() = id);

drop policy if exists "health_profiles_select_own" on public.health_profiles;
create policy "health_profiles_select_own"
on public.health_profiles
for select
using (auth.uid() = user_id);

drop policy if exists "health_profiles_insert_own" on public.health_profiles;
create policy "health_profiles_insert_own"
on public.health_profiles
for insert
with check (auth.uid() = user_id);

drop policy if exists "health_profiles_update_own" on public.health_profiles;
create policy "health_profiles_update_own"
on public.health_profiles
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "health_profiles_delete_own" on public.health_profiles;
create policy "health_profiles_delete_own"
on public.health_profiles
for delete
using (auth.uid() = user_id);

drop policy if exists "daily_logs_select_own" on public.daily_logs;
create policy "daily_logs_select_own"
on public.daily_logs
for select
using (auth.uid() = user_id);

drop policy if exists "daily_logs_insert_own" on public.daily_logs;
create policy "daily_logs_insert_own"
on public.daily_logs
for insert
with check (auth.uid() = user_id);

drop policy if exists "daily_logs_update_own" on public.daily_logs;
create policy "daily_logs_update_own"
on public.daily_logs
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "daily_logs_delete_own" on public.daily_logs;
create policy "daily_logs_delete_own"
on public.daily_logs
for delete
using (auth.uid() = user_id);

drop policy if exists "stress_entries_select_own" on public.stress_entries;
create policy "stress_entries_select_own"
on public.stress_entries
for select
using (auth.uid() = user_id);

drop policy if exists "stress_entries_insert_own" on public.stress_entries;
create policy "stress_entries_insert_own"
on public.stress_entries
for insert
with check (auth.uid() = user_id);

drop policy if exists "stress_entries_update_own" on public.stress_entries;
create policy "stress_entries_update_own"
on public.stress_entries
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "stress_entries_delete_own" on public.stress_entries;
create policy "stress_entries_delete_own"
on public.stress_entries
for delete
using (auth.uid() = user_id);

drop policy if exists "wellness_goals_select_own" on public.wellness_goals;
create policy "wellness_goals_select_own"
on public.wellness_goals
for select
using (auth.uid() = user_id);

drop policy if exists "wellness_goals_insert_own" on public.wellness_goals;
create policy "wellness_goals_insert_own"
on public.wellness_goals
for insert
with check (auth.uid() = user_id);

drop policy if exists "wellness_goals_update_own" on public.wellness_goals;
create policy "wellness_goals_update_own"
on public.wellness_goals
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "wellness_goals_delete_own" on public.wellness_goals;
create policy "wellness_goals_delete_own"
on public.wellness_goals
for delete
using (auth.uid() = user_id);

drop policy if exists "gratitude_entries_select_own" on public.gratitude_entries;
create policy "gratitude_entries_select_own"
on public.gratitude_entries
for select
using (auth.uid() = user_id);

drop policy if exists "gratitude_entries_insert_own" on public.gratitude_entries;
create policy "gratitude_entries_insert_own"
on public.gratitude_entries
for insert
with check (auth.uid() = user_id);

drop policy if exists "gratitude_entries_update_own" on public.gratitude_entries;
create policy "gratitude_entries_update_own"
on public.gratitude_entries
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "gratitude_entries_delete_own" on public.gratitude_entries;
create policy "gratitude_entries_delete_own"
on public.gratitude_entries
for delete
using (auth.uid() = user_id);

commit;
