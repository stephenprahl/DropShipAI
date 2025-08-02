from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base, func

class ProductSeller(Base):
    __tablename__ = 'product_sellers'

    product_id = Column(Integer, ForeignKey('products.id'), primary_key=True)
    seller_id = Column(Integer, ForeignKey('sellers.id'), primary_key=True)
    price = Column(Float, nullable=False)
    shipping_price = Column(Float, default=0.0)
    is_available = Column(Boolean, default=True)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="sellers")
    seller = relationship("Seller", back_populates="products")

    def __repr__(self):
        return f"<ProductSeller(product_id={self.product_id}, seller_id={self.seller_id}, price={self.price})>"
