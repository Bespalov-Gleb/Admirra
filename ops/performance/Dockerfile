ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG APP_RELEASE
LABEL org.opencontainers.image.revision=${APP_RELEASE}
# Verify the reviewed live source, not the unrelated host Git checkout.
COPY ops/performance/verify_base.py /tmp/verify-summary-base.py
RUN python /tmp/verify-summary-base.py && rm /tmp/verify-summary-base.py
COPY backend_api/stats_service.py backend_api/stats.py backend_api/clients.py backend_api/folders.py backend_api/summary_scope.py backend_api/summary_facts.py /app/backend_api/
COPY core/schemas.py /app/core/schemas.py
COPY core/runtime.py /app/core/runtime.py
COPY ai/report_generator.py /app/ai/report_generator.py
