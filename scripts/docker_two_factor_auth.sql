-- Двухэтапная аутентификация: подтверждение почты + OTP при входе
-- Выполнить в Docker: docker compose exec db psql -U postgres -d saas_project -f - < scripts/docker_two_factor_auth.sql
-- Или по одной команде -c (PostgreSQL)

ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token_hash VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_expires_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_email_last_sent_at TIMESTAMPTZ;

-- Существующие пользователи — считаем почту подтверждённой (не блокировать прод)
UPDATE users SET email_verified = true WHERE email_verified IS NOT DISTINCT FROM false;

CREATE TABLE IF NOT EXISTS login_otp_challenges (
    id UUID PRIMARY KEY,
    challenge_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_hash VARCHAR NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_login_otp_challenges_challenge_id ON login_otp_challenges (challenge_id);
CREATE INDEX IF NOT EXISTS ix_login_otp_challenges_user_id ON login_otp_challenges (user_id);
