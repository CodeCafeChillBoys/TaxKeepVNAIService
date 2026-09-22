import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base
from app.enum import TaxRuleStatus

if TYPE_CHECKING:
    from app.models.tax_rule import TaxRule


class TaxRuleSet(Base):
    __tablename__ = "tax_rule_sets"

    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    effective_from: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g. "2026-01-01"
    effective_to: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # e.g. "2027-01-01"
    status: Mapped[str] = mapped_column(String(50), default=TaxRuleStatus.DRAFT.value, nullable=False) # Draft, Active, Expired
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    rules: Mapped[List["TaxRule"]] = relationship(
        "TaxRule", back_populates="rule_set", cascade="all, delete-orphan"
    )
