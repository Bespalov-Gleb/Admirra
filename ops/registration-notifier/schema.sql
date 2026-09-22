-- Additive, independent of the pending application/worker cutover.
-- Run as database owner inside a transaction; no historical enqueue.
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '15s';
CREATE SCHEMA IF NOT EXISTS registration_notifier;
REVOKE ALL ON SCHEMA registration_notifier FROM PUBLIC;
CREATE TABLE IF NOT EXISTS registration_notifier.outbox (
    user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    state text NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending', 'sending', 'sent', 'failed', 'uncertain')),
    available_at timestamptz NOT NULL DEFAULT (clock_timestamp() + interval '10 seconds'),
    attempts integer NOT NULL DEFAULT 0,
    lease_token uuid,
    lease_until timestamptz,
    finished_at timestamptz,
    message_id bigint,
    error_code text
);
CREATE INDEX IF NOT EXISTS registration_notifier_pending
    ON registration_notifier.outbox (available_at, created_at) WHERE state = 'pending';
CREATE OR REPLACE FUNCTION registration_notifier.enqueue() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    INSERT INTO registration_notifier.outbox (user_id) VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION registration_notifier.enqueue() FROM PUBLIC;
-- Re-installation changes the trigger atomically, without touching queue state.
DROP TRIGGER IF EXISTS admirra_registration_notify ON public.users;
CREATE TRIGGER admirra_registration_notify AFTER INSERT ON public.users
FOR EACH ROW EXECUTE FUNCTION registration_notifier.enqueue();
