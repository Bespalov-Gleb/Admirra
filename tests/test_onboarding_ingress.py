import pytest
from ops.onboarding_ingress import drained

UP = '''upstream admirra_api_read_canary {
    least_conn;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=5s;
    server 10.77.0.2:8001 weight=1 max_fails=3 fail_timeout=5s;
    keepalive 16;
}'''
SITE = 'proxy_pass http://127.0.0.1:8001;\nproxy_pass http://127.0.0.1:8001/docs;\nproxy_pass http://127.0.0.1:8001/openapi.json;\nproxy_next_upstream off;'

def test_drain_api2_keeps_primary_locations():
    up, site = drained(UP, SITE, 'api2')
    assert '10.77.0.2:8001 weight=1 max_fails=3 fail_timeout=5s down;' in up
    assert site == SITE and up.count(' down;') == 1

def test_drain_api1_routes_no_retry_paths_to_healthy_api2():
    up, site = drained(UP, SITE, 'api1')
    assert '127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=5s down;' in up
    assert site.count('http://10.77.0.2:8001') == 3
    assert 'proxy_next_upstream off;' in site

def test_drift_is_rejected():
    with pytest.raises(ValueError): drained(UP.replace('weight=1','weight=2'),SITE,'api2')
    with pytest.raises(ValueError): drained(UP,SITE.replace('/docs','/docsxxx').replace('127.0.0.1:8001/docsxxx','other'),'api1')
