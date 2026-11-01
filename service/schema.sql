-- The database the Bawabu service expects (Supabase / Postgres). The hosted project was built up through migrations;
-- this is the resulting schema, for running your own copy. Run it once on a fresh project (SQL editor or psql).
--
-- Row-level security is on with no policies: the anon and signed-in keys can't read or write anything. Only the
-- service, with the project's secret key (server side, in a Modal secret), uses these tables.

-- One verdict per exact package version and registry, so each version is judged once.
create table public.verdicts (
  id uuid primary key default gen_random_uuid(),
  ecosystem text not null check (ecosystem in ('npm', 'pypi')),
  -- '' for the public registry; otherwise the private registry's URL, so a private "foo" never shares a verdict
  -- with the public "foo".
  registry text not null default '' check (char_length(registry) <= 512),
  name text not null check (char_length(name) between 1 and 214),
  version text not null check (char_length(version) between 1 and 256),
  verdict text not null check (verdict in ('allow', 'block', 'ask')),
  reason text not null,
  -- Which version of the checks made it; lookups ignore verdicts from older engines.
  engine integer not null check (engine >= 0),
  signals jsonb not null default '[]'::jsonb check (jsonb_typeof(signals) = 'array'),
  suggestion text check (suggestion is null or char_length(suggestion) between 1 and 214),
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint verdicts_ecosystem_registry_name_version_key unique (ecosystem, registry, name, version)
);
comment on table public.verdicts is 'Bawabu verdict cache: one row per exact package version. Written by the service with the secret key.';
alter table public.verdicts enable row level security;

-- One row per investigation (sandbox + diff + Muse Spark); `result` is the verdict with its evidence.
create table public.investigations (
  id uuid primary key default gen_random_uuid(),
  ecosystem text not null check (ecosystem in ('npm', 'pypi')),
  registry text not null default '' check (char_length(registry) <= 512),
  name text not null check (char_length(name) between 1 and 214),
  version text not null check (char_length(version) between 1 and 256),
  status text not null default 'running' check (status in ('running', 'done', 'failed')),
  result jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index investigations_package_idx on public.investigations (ecosystem, registry, name, version, created_at desc);
alter table public.investigations enable row level security;

-- Each investigation's steps, in order: what the report page streams.
create table public.investigation_events (
  investigation_id uuid not null references public.investigations (id) on delete cascade,
  seq integer not null check (seq >= 0),
  event jsonb not null,
  created_at timestamptz not null default now(),
  primary key (investigation_id, seq)
);
alter table public.investigation_events enable row level security;
