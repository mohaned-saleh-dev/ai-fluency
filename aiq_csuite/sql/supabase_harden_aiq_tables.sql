-- AiQ: lock down public.sessions / messages / events for Supabase PostgREST
-- Run once in Supabase SQL Editor (or rely on init_db() which runs the same for new deploys).
--
-- Why: Supabase exposes `public` tables to the Data API (anon + authenticated JWT roles).
-- These tables hold transcripts and metadata — they must NOT be world-readable.
--
-- Effect:
--   * ENABLE ROW LEVEL SECURITY with no permissive policies ⇒ anon/authenticated
--     cannot SELECT/INSERT/UPDATE/DELETE any rows (default deny).
--   * Your Flask app uses DATABASE_URL as role `postgres` (table owner) ⇒ owners
--     bypass RLS in PostgreSQL ⇒ app behaviour unchanged.
--
-- If you ever need browser-direct reads, add explicit RLS policies for authenticated
-- users — do not remove RLS without replacing it with another control.

ALTER TABLE IF EXISTS public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.events ENABLE ROW LEVEL SECURITY;

-- Defense in depth: strip API role grants if they were inherited from defaults.
REVOKE ALL ON TABLE public.sessions FROM PUBLIC;
REVOKE ALL ON TABLE public.messages FROM PUBLIC;
REVOKE ALL ON TABLE public.events FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.sessions FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.messages FROM anon';
    EXECUTE 'REVOKE ALL ON TABLE public.events FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.sessions FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.messages FROM authenticated';
    EXECUTE 'REVOKE ALL ON TABLE public.events FROM authenticated';
  END IF;
END $$;
