from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from .base import Base

class Seller(Base):
    __tablename__ = 'sellers'

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False)
    seller_id = Column(String, nullable=False)
    name = Column(String)
    rating = Column(Float)
    total_ratings = Column(Integer)
    positive_feedback_percent = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    products = relationship("ProductSeller", back_populates="seller")

    __table_args__ = (
        UniqueConstraint('platform', 'seller_id', name='uq_seller_platform'),
    )

    def __repr__(self):
        return f"<Seller(id={self.id}, name='{self.name}', platform='{self.platform}'>"
