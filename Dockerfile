FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

WORKDIR /app

# Install system dependencies (incl. WeasyPrint for PDF reports: Pango, GObject, Cairo)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    postgresql-client \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# MAX API uses a certificate chain issued by the Russian trusted CA.  Keep the
# two certificates in the image trust store instead of weakening TLS checks.
COPY certs/russian_trusted_root_ca.crt /usr/local/share/ca-certificates/admirra/russian_trusted_root_ca.crt
COPY certs/russian_trusted_sub_ca.crt.b64 /tmp/russian_trusted_sub_ca.crt.b64
RUN base64 --decode /tmp/russian_trusted_sub_ca.crt.b64 > /usr/local/share/ca-certificates/admirra/russian_trusted_sub_ca.crt \
    && rm /tmp/russian_trusted_sub_ca.crt.b64 \
    && update-ca-certificates

# Copy requirements and install python dependencies
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock && pip check

# Copy project files
COPY . .
# The reviewed source archive can be extracted under a restrictive umask.
# Source directories must remain traversable by the unprivileged runtime/test
# user, without granting writes or changing ownership. Secrets are excluded by
# the build-context allowlist; credentials are injected only at runtime.
RUN chmod -R a+rX /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8001
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ARG APP_RELEASE=unknown
ENV APP_RELEASE=${APP_RELEASE}
LABEL org.opencontainers.image.revision=${APP_RELEASE}

EXPOSE 8001

# Run the application
CMD ["uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
