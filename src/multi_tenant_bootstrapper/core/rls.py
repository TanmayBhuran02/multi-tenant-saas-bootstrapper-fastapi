"""Row-Level Security via SQLAlchemy ORM events.

Implements application-level tenant isolation using ContextVars and
SQLAlchemy's ``do_orm_execute`` event. This automatically filters all
queries on models that have a ``tenant_id`` column to the current
tenant context.

Usage::

    from multi_tenant_bootstrapper import set_tenant_id, bypass_rls

    # Normal query — automatically filtered to current tenant
    set_tenant_id("some-uuid")
    result = await db.execute(select(User))  # Only current tenant's users

    # Superadmin query — bypasses RLS
    with bypass_rls():
        result = await db.execute(select(User))  # ALL users across tenants
"""

import contextvars
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.orm import Session

# ── Context Variables ────────────────────────────────────────────────────────
_current_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    'tenant_id', default=None
)
_bypass_rls: contextvars.ContextVar[bool] = contextvars.ContextVar(
    'bypass_rls', default=False
)


def set_tenant_id(tid: str) -> None:
    """Set the current tenant context for query filtering."""
    _current_tenant_id.set(tid)


def get_tenant_id() -> str | None:
    """Get the current tenant context."""
    return _current_tenant_id.get()


def clear_tenant_id() -> None:
    """Clear the current tenant context."""
    _current_tenant_id.set(None)


@contextmanager
def bypass_rls():
    """Context manager to bypass RLS for superadmin / cross-tenant operations.

    Usage::

        with bypass_rls():
            result = await db.execute(select(Tenant))  # returns ALL tenants
    """
    token = _bypass_rls.set(True)
    try:
        yield
    finally:
        _bypass_rls.reset(token)


def _has_tenant_id_column(mapper) -> bool:
    """Check if a mapped class has a tenant_id column."""
    try:
        columns = {col.key for col in mapper.columns}
        return 'tenant_id' in columns
    except Exception:
        return False


_rls_registered: bool = False


def register_rls_listener() -> None:
    """Register the RLS query filter on the SQLAlchemy Session.

    Call this once during app initialization. Safe to call multiple times
    — subsequent calls are no-ops.
    """
    global _rls_registered
    if _rls_registered:
        return
    _rls_registered = True

    @event.listens_for(Session, 'do_orm_execute')
    def _apply_tenant_filter(orm_execute_state):
        # Skip if RLS is bypassed (superadmin context)
        if _bypass_rls.get():
            return

        # Only filter SELECT statements
        if not orm_execute_state.is_select:
            return

        # Skip column loads (lazy loads) to avoid recursion
        if orm_execute_state.is_column_load:
            return

        # Skip relationship loads to avoid issues with joined queries
        if orm_execute_state.is_relationship_load:
            return

        tenant_id = _current_tenant_id.get()
        if tenant_id is None:
            return

        # Get the mapped entities from the statement
        mapper = orm_execute_state.bind_mapper
        if mapper is None:
            return

        if _has_tenant_id_column(mapper):
            # Get the model class and add tenant filter
            model_class = mapper.class_
            orm_execute_state.statement = orm_execute_state.statement.options(
            ).where(model_class.tenant_id == tenant_id)
