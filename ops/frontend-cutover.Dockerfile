# Overlay a clean, tested dist on the preserved production frontend image.
# The operator must verify/tag the expected base digest before building.
# Keep older hashed chunks so already-open clients can finish navigation.
ARG FRONTEND_BASE=admirra-frontend:cutover-base-c66a577
FROM ${FRONTEND_BASE}
ARG FRONTEND_RELEASE
LABEL org.opencontainers.image.revision=${FRONTEND_RELEASE}
COPY dist/ /usr/share/nginx/html/
