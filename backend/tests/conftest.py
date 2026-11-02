"""Identidade sintética para os testes antigos dos contratos de negócio."""

from uuid import UUID

import pytest

from app.main import app
from app.security.dependencies import get_current_user


def _admin_for_business_contracts():
    return {
        "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
        "nome": "Administrador de teste",
        "email": "admin@example.invalid",
        "perfil": "ADMIN_TI",
    }


class _BusinessOverrides(dict):
    """Preserva a identidade entre os resets de overrides dos testes antigos."""

    def clear(self) -> None:
        super().clear()
        self[get_current_user] = _admin_for_business_contracts


@pytest.fixture(autouse=True)
def authenticated_business_contracts(request):
    """Executa testes anteriores de negócio como ADMIN_TI; RBAC tem testes próprios."""
    name = request.path.name
    business_modules = (
        "test_filters_",
        "test_metrics_",
        "test_revenue_",
        "test_network_",
        "test_inspection",
        "test_uc_",
        "test_agent_usage_",
    )
    if not (name.startswith(business_modules) or name == "test_uc.py"):
        yield
        return

    original = app.dependency_overrides
    app.dependency_overrides = _BusinessOverrides(original)
    app.dependency_overrides[get_current_user] = _admin_for_business_contracts
    try:
        yield
    finally:
        app.dependency_overrides = original
