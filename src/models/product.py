from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    source_platform = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    original_price = Column(Float)
    currency = Column(String, default='USD')
    url = Column(String, nullable=False)
    image_url = Column(String)
    category = Column(String)
    brand = Column(String)
    model = Column(String)
    condition = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    sellers = relationship("ProductSeller", back_populates="product")
    arbitrage_opportunities = relationship("ArbitrageOpportunity", back_populates="product")
    sales_history = relationship("SalesHistory", back_populates="product")

    __table_args__ = (
        UniqueConstraint('source_platform', 'source_id', name='uq_product_source'),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title}', price={self.price}{self.currency}>"
