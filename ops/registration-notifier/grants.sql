-- Role must already exist, with a separately generated password.
GRANT USAGE ON SCHEMA public, registration_notifier TO admirra_registration_notifier;
GRANT SELECT (id, first_name, last_name, username, email, phone, created_at,
    email_verified, registration_utm_source, registration_utm_medium,
    registration_utm_campaign) ON public.users TO admirra_registration_notifier;
GRANT SELECT (user_id, provider, created_at) ON public.user_oauth_identities
    TO admirra_registration_notifier;
GRANT SELECT, UPDATE ON registration_notifier.outbox TO admirra_registration_notifier;
