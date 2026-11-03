"""Matriz aprovada por método HTTP e padrão de rota FastAPI."""

ALL_PROFILES = frozenset({"DIRETORIA", "ATENDIMENTO", "PERDAS", "OPERACAO", "ADMIN_TI"})
DIRECTORS = frozenset({"DIRETORIA", "ADMIN_TI"})
CUSTOMER_SERVICE = frozenset({"ATENDIMENTO", "PERDAS", "ADMIN_TI"})
LOSSES = frozenset({"PERDAS", "ADMIN_TI"})
OPERATIONS = frozenset({"DIRETORIA", "OPERACAO", "ADMIN_TI"})
ADMIN_ONLY = frozenset({"ADMIN_TI"})

PUBLIC_ROUTES = frozenset(
    {
        ("GET", "/api/health"),
        ("GET", "/api/docs"),
        ("GET", "/api/openapi.json"),
        ("GET", "/api/redoc"),
        ("POST", "/api/auth/login"),
    }
)

ROUTE_PERMISSIONS: dict[tuple[str, str], frozenset[str]] = {
    ("GET", "/api/auth/me"): ALL_PROFILES,
    ("POST", "/api/auth/logout"): ALL_PROFILES,
    ("PATCH", "/api/auth/password"): ALL_PROFILES,
    ("POST", "/api/auth/users"): ADMIN_ONLY,
    ("GET", "/api/filters/options"): ALL_PROFILES,
    ("GET", "/api/metrics/general"): DIRECTORS,
    ("GET", "/api/metrics/revenue-variance"): DIRECTORS,
    ("GET", "/api/uc/{uc_id}/360"): CUSTOMER_SERVICE,
    ("GET", "/api/network/continuity"): OPERATIONS,
    ("GET", "/api/inspections/queue"): LOSSES,
    ("GET", "/api/inspections/queue/export"): LOSSES,
    ("GET", "/api/inspections/orders"): LOSSES,
    ("POST", "/api/inspections/order"): LOSSES,
    ("PATCH", "/api/inspections/{id}"): LOSSES,
    ("DELETE", "/api/inspections/{id}"): LOSSES,
    ("POST", "/api/ai/ask"): ALL_PROFILES,
    ("GET", "/api/ai/insights/{tela}/{entidade_id}"): CUSTOMER_SERVICE,
    ("POST", "/api/ai/feedback"): ALL_PROFILES,
    ("GET", "/api/ai/audit/{audit_id}"): ADMIN_ONLY,
    ("GET", "/api/ai/usage"): ADMIN_ONLY,
    ("GET", "/api/ai/evaluations"): ADMIN_ONLY,
}
