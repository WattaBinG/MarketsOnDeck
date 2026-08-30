-- Markets On Deck OS — Core Schema (Community Leaderboard MVP)
-- Design principle carried over from the original hypothesis-tracker concept:
-- predictions are immutable once posted; grading happens in a separate,
-- append-only table that regular users cannot write to directly.

-- 1. Profiles — one row per registered user, extends Supabase's built-in auth.users
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null,
  display_name text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Profiles are publicly readable"
  on public.profiles for select
  using (true);

create policy "Users can insert their own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

create policy "Users can update their own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Auto-create a profile row whenever a new user signs up via Supabase Auth
create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, username, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'username', 'trader_' || substr(new.id::text, 1, 8)),
    coalesce(new.raw_user_meta_data->>'display_name', new.raw_user_meta_data->>'username')
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2. Predictions — the immutable call log. INSERT and SELECT only, no UPDATE/DELETE
-- for anyone (including the author) once posted — that's the integrity guarantee.
create table public.predictions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  ticker text not null,
  direction text not null check (direction in ('up', 'down')),
  price_target numeric,
  price_at_prediction numeric not null,
  target_date date not null,
  confidence smallint check (confidence between 1 and 5),
  thesis text,
  created_at timestamptz not null default now(),
  constraint target_date_in_future check (target_date > created_at::date)
);

alter table public.predictions enable row level security;

create policy "Predictions are publicly readable"
  on public.predictions for select
  using (true);

create policy "Users can post their own predictions"
  on public.predictions for insert
  with check (auth.uid() = user_id);

-- Deliberately no UPDATE or DELETE policy for any role except service_role
-- (service_role bypasses RLS entirely, used only by the verification job for
-- corrections if ever needed — never by end users).

-- 3. Resolutions — separate, append-only grading table. Only the automated
-- verification job (service role) writes here; everyone can read.
create table public.resolutions (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid not null references public.predictions(id) on delete cascade unique,
  resolved_price numeric not null,
  outcome text not null check (outcome in ('win', 'loss')),
  resolution_method text not null default 'automated',
  resolved_at timestamptz not null default now()
);

alter table public.resolutions enable row level security;

create policy "Resolutions are publicly readable"
  on public.resolutions for select
  using (true);

-- No insert/update/delete policy for authenticated/anon roles at all —
-- only service_role (used by the scheduled job) can write, since it bypasses RLS.

-- 4. Leaderboard — a live view, not a stored table, so it's always accurate
-- without needing manual refresh.
create view public.leaderboard as
select
  p.id as user_id,
  p.username,
  p.display_name,
  count(r.id) as resolved_predictions,
  count(r.id) filter (where r.outcome = 'win') as wins,
  count(r.id) filter (where r.outcome = 'loss') as losses,
  case when count(r.id) > 0
    then round(100.0 * count(r.id) filter (where r.outcome = 'win') / count(r.id), 2)
    else null
  end as win_rate_pct,
  count(pr.id) as total_predictions,
  count(pr.id) filter (where r.id is null) as pending_predictions
from public.profiles p
left join public.predictions pr on pr.user_id = p.id
left join public.resolutions r on r.prediction_id = pr.id
group by p.id, p.username, p.display_name;

comment on table public.predictions is 'Immutable prediction log. No UPDATE/DELETE policy exists for any user-facing role by design — this is the integrity guarantee the whole product is built on.';
comment on table public.resolutions is 'Append-only grading records, written only by the automated verification job (service role). Never editable by the predicting user.';
