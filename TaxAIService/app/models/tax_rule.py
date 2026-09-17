import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.tax_rule_set import TaxRuleSet
    from app.models.dependent_rule import DependentRule


class TaxRule(Base):
    __tablename__ = "tax_rules"

    # Primary key dạng GUID (UUID)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    # Khóa ngoại liên kết tới TaxRuleSet.rule_set_id (dạng GUID)
    rule_set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_rule_sets.rule_set_id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False) # DEDUCTION, RATE, BRACKET, EXEMPTION
    condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # VND/month, %
    effective_from: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    effective_to: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legal_document: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    article: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    clause: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    point: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False) # Draft, Active, Expired
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    rule_set: Mapped[Optional["TaxRuleSet"]] = relationship("TaxRuleSet", back_populates="rules")
    dependent_rules: Mapped[List["DependentRule"]] = relationship(
        "DependentRule", back_populates="rule", cascade="all, delete-orphan"
    )
