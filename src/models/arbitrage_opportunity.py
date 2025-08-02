from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base, func

class ArbitrageOpportunity(Base):
    __tablename__ = 'arbitrage_opportunities'

    id = Column(Integer, primary_key=True, index=True)
    source_product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    target_platform = Column(String, nullable=False)
    estimated_selling_price = Column(Float, nullable=False)
    estimated_fees = Column(Float, nullable=False)
    estimated_profit = Column(Float, nullable=False)
    profit_margin = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="arbitrage_opportunities")

    def __repr__(self):
        return f"<ArbitrageOpportunity(id={self.id}, profit={self.estimated_profit}, margin={self.profit_margin}%)>"
