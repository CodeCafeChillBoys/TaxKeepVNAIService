import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.tax_rule import TaxRule


class DependentRule(Base):
    __tablename__ = "dependent_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_rules.rule_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dependent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # CHILD, ADULT_CHILD, SPOUSE, PARENT, OTHER
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_monthly_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_studying: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False) # Draft, Active, Expired
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    rule: Mapped["TaxRule"] = relationship("TaxRule", back_populates="dependent_rules")

    @property
    def rule_set_id(self) -> Optional[uuid.UUID]:
        """Thuộc tính tương thích ngược để lấy rule_set_id thông qua TaxRule cha."""
        return self.rule.rule_set_id if self.rule else None
