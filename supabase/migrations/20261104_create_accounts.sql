create table if not exists public.accounts (
  key text primary key,
  feed_token text unique not null,
  name text,
  profile jsonb,
  profile_ts bigint not null default 0,
  picks jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
-- Only the service role (edge functions) may touch this table; the anon key gets nothing.
alter table public.accounts enable row level security;
revoke all on public.accounts from anon, authenticated;
create index if not exists accounts_feed_token_idx on public.accounts (feed_token);
