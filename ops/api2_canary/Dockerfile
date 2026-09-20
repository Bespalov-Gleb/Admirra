ARG BASE_IMAGE
FROM ${BASE_IMAGE}
LABEL ru.admirra.role="api-replica" \
      ru.admirra.release="api2-production-compatible-20260920-v2"
COPY build_overlay.py /tmp/build_overlay.py
RUN python /tmp/build_overlay.py && rm /tmp/build_overlay.py
