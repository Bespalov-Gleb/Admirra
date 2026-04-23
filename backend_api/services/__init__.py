"""
Совместимость импорта:
- backend_api.services.auth_mail (новый пакетный импорт)
- backend_api.services.IntegrationService (legacy импорт из backend_api/services.py)
"""

from pathlib import Path
import importlib.util


_LEGACY_PATH = Path(__file__).resolve().parent.parent / "services.py"
_spec = importlib.util.spec_from_file_location("backend_api._legacy_services", _LEGACY_PATH)
if _spec and _spec.loader:
    _legacy_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_legacy_module)
    IntegrationService = _legacy_module.IntegrationService
else:
    raise ImportError(f"Cannot load legacy IntegrationService from {_LEGACY_PATH}")

__all__ = ["IntegrationService"]
