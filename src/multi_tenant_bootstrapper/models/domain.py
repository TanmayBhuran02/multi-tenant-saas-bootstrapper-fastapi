"""Domain models for multi-tenant SaaS applications."""

import enum
from sqlalchemy import (
    Column, String, Boolean, Enum, ForeignKey, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from multi_tenant_bootstrapper.core.security import get_password_hash, verify_password
from multi_tenant_bootstrapper.models.base import Base, TimestampMixin, SerializerMixin

# ── Enums ────────────────────────────────────────────────────────────────────

class PlanType(enum.Enum):
    free = 'free'
    starter = 'starter'
    pro = 'pro'
    enterprise = 'enterprise'

class TenantStatus(enum.Enum):
    active = 'active'
    suspended = 'suspended'
    deleted = 'deleted'

class UserRole(enum.Enum):
    owner = 'owner'
    admin = 'admin'
    member = 'member'

# ── Tenant ───────────────────────────────────────────────────────────────────

class Tenant(Base, TimestampMixin, SerializerMixin):
    __tablename__ = 'tenants'

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    slug = Column(String(50), unique=True, nullable=False, index=True)
    subdomain = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    plan = Column(
        Enum(PlanType, name='plan_type', create_constraint=True),
        default=PlanType.free,
        nullable=False,
    )
    status = Column(
        Enum(TenantStatus, name='tenant_status', create_constraint=True),
        default=TenantStatus.active,
        nullable=False,
    )

    configs = relationship('TenantConfig', back_populates='tenant', cascade='all, delete-orphan')
    users = relationship('User', back_populates='tenant', cascade='all, delete-orphan')
    feature_flags = relationship('FeatureFlag', back_populates='tenant', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tenant {self.slug} ({self.plan.value})>'

# ── TenantConfig ─────────────────────────────────────────────────────────────

class TenantConfig(Base, TimestampMixin, SerializerMixin):
    __tablename__ = 'tenant_configs'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'key', name='uq_tenant_config_key'),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    key = Column(String(100), nullable=False)
    value = Column(JSONB, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)

    tenant = relationship('Tenant', back_populates='configs')

    def __repr__(self):
        return f'<TenantConfig {self.key}>'

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude=exclude)
        if self.is_secret:
            data['value'] = '********'
        return data

# ── User ─────────────────────────────────────────────────────────────────────

class User(Base, TimestampMixin, SerializerMixin):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_user_tenant_email'),
    )

    _serialize_exclude = {'hashed_password'}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, name='user_role', create_constraint=True),
        default=UserRole.member,
        nullable=False,
    )
    is_superadmin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    tenant = relationship('Tenant', back_populates='users')

    def set_password(self, password):
        self.hashed_password = get_password_hash(password)

    def check_password(self, password):
        return verify_password(password, self.hashed_password)

    def __repr__(self):
        return f'<User {self.email} ({self.role.value})>'

# ── FeatureFlag ──────────────────────────────────────────────────────────────

class FeatureFlag(Base, TimestampMixin, SerializerMixin):
    __tablename__ = 'feature_flags'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'flag_name', name='uq_tenant_flag_name'),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    flag_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    payload = Column(JSONB, nullable=True)
    plan_min = Column(
        Enum(PlanType, name='plan_type', create_constraint=True, create_type=False),
        nullable=True,
    )

    tenant = relationship('Tenant', back_populates='feature_flags')

    def __repr__(self):
        return f'<FeatureFlag {self.flag_name} enabled={self.enabled}>'
