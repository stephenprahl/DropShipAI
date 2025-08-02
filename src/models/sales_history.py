from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from .base import Base, func

class SalesHistory(Base):
    __tablename__ = 'sales_history'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    platform = Column(String, nullable=False)
    sale_price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    fees = Column(Float, nullable=False)
    shipping_cost = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    sale_date = Column(DateTime, server_default=func.now())
    notes = Column(Text)

    # Relationships
    product = relationship("Product", back_populates="sales_history")

    def __repr__(self):
        return f"<SalesHistory(id={self.id}, product_id={self.product_id}, sale_price={self.sale_price}, date={self.sale_date})>"
