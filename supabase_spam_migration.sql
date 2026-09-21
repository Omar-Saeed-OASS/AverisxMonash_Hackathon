-- Run this migration in the Supabase SQL editor.
-- The application uses the service-role key for these server-side writes.

alter table public.emails
  add column if not exists category text,
  add column if not exists metadata jsonb not null default '{}'::jsonb;

-- Remove these only if they were created by an earlier version of this migration.
alter table public.emails
  drop column if exists sender_email,
  drop column if exists is_spam,
  drop column if exists spam_score,
  drop column if exists spam_reasons,
  drop column if exists spam_action,
  drop column if exists is_blacklisted;

create table if not exists public.sender_reputation (
  sender_email text primary key,
  sender_name text,
  spam_count integer not null default 0,
  is_blacklisted boolean not null default false,
  last_spam_at timestamptz,
  last_spam_reason text,
  last_spam_score numeric,
  blacklist_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists sender_reputation_blacklisted_idx
  on public.sender_reputation (is_blacklisted)
  where is_blacklisted = true;