"""
Database utility module using SQLAlchemy ORM with Neon database.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, and_, or_, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session, Session, declarative_base, relationship
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Create engine and session factory
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

# Base class for all models
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database by creating all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

# Models
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
        {'sqlite_autoincrement': True},
    )

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
        {'sqlite_autoincrement': True},
    )

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

# Database utility class
class Database:
    def __init__(self):
        """Initialize the database session."""
        self.session = SessionLocal()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Close the database session."""
        try:
            self.session.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
            raise
    
    # Generic CRUD operations
    def get(self, model: Type[Base], id: Any) -> Optional[Base]:
        """Get a single record by ID."""
        try:
            return self.session.query(model).get(id)
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__} with id {id}: {e}")
            self.session.rollback()
            raise
    
    def get_by_field(self, model: Type[Base], field: str, value: Any) -> Optional[Base]:
        """Get a single record by field value."""
        try:
            return self.session.query(model).filter(getattr(model, field) == value).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__} by {field}={value}: {e}")
            self.session.rollback()
            raise
    
    def get_multi(
        self, 
        model: Type[Base], 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict] = None,
        order_by: Optional[str] = None
    ) -> List[Base]:
        """Get multiple records with optional filtering and pagination."""
        try:
            query = self.session.query(model)
            
            # Apply filters if provided
            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(model, field):
                        if isinstance(value, (list, tuple)):
                            conditions.append(getattr(model, field).in_(value))
                        else:
                            conditions.append(getattr(model, field) == value)
                if conditions:
                    query = query.filter(and_(*conditions))
            
            # Apply ordering if provided
            if order_by:
                order_field = order_by.lstrip('-')
                if order_by.startswith('-'):
                    query = query.order_by(desc(getattr(model, order_field, 'id')))
                else:
                    query = query.order_by(getattr(model, order_field, 'id'))
            
            return query.offset(skip).limit(limit).all()
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {model.__name__} records: {e}")
            self.session.rollback()
            raise
    
    def create(self, model: Type[Base], obj_in: Union[Dict, Any]) -> Base:
        """Create a new record."""
        try:
            if isinstance(obj_in, dict):
                db_obj = model(**obj_in)
            else:
                db_obj = obj_in
                
            self.session.add(db_obj)
            self.session.commit()
            self.session.refresh(db_obj)
            return db_obj
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error creating {model.__name__}: {e}")
            raise
    
    def update(
        self, 
        model: Type[Base], 
        db_obj: Base, 
        obj_in: Union[Dict, Any]
    ) -> Base:
        """Update an existing record."""
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)
            
            for field, value in update_data.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)
            
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = datetime.utcnow()
                
            self.session.add(db_obj)
            self.session.commit()
            self.session.refresh(db_obj)
            return db_obj
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating {model.__name__}: {e}")
            raise
    
    def delete(self, model: Type[Base], id: int) -> bool:
        """Delete a record by ID."""
        try:
            obj = self.session.query(model).get(id)
            if obj:
                self.session.delete(obj)
                self.session.commit()
                return True
            return False
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error deleting {model.__name__} with id {id}: {e}")
            raise
    
    # Product-specific methods
    def add_or_update_product(self, product_data: dict) -> int:
        """
        Add a new product or update an existing one.
        Returns the product ID.
        """
        try:
            # Check if product exists
            product = self.session.query(Product).filter(
                Product.source_platform == product_data['source_platform'],
                Product.source_id == product_data['source_id']
            ).first()
            
            if product:
                # Update existing product
                update_data = {}
                for field in ['title', 'description', 'price', 'original_price', 'url', 
                            'image_url', 'category', 'brand', 'model', 'condition', 'currency']:
                    if field in product_data and product_data[field] is not None:
                        update_data[field] = product_data[field]
                
                if update_data:
                    for key, value in update_data.items():
                        setattr(product, key, value)
                    self.session.add(product)
                    self.session.commit()
                    self.session.refresh(product)
                
                return product.id
            else:
                # Create new product
                new_product = Product(
                    source_platform=product_data['source_platform'],
                    source_id=product_data['source_id'],
                    title=product_data.get('title', ''),
                    description=product_data.get('description'),
                    price=product_data['price'],
                    original_price=product_data.get('original_price', product_data['price']),
                    currency=product_data.get('currency', 'USD'),
                    url=product_data['url'],
                    image_url=product_data.get('image_url'),
                    category=product_data.get('category'),
                    brand=product_data.get('brand'),
                    model=product_data.get('model'),
                    condition=product_data.get('condition')
                )
                self.session.add(new_product)
                self.session.commit()
                self.session.refresh(new_product)
                return new_product.id
                
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding/updating product: {e}")
            raise
    
    def add_seller(self, seller_data: dict) -> int:
        """
        Add a new seller or update an existing one.
        Returns the seller ID.
        """
        try:
            # Check if seller exists
            seller = self.session.query(Seller).filter(
                Seller.platform == seller_data['platform'],
                Seller.seller_id == seller_data['seller_id']
            ).first()
            
            if seller:
                # Update existing seller
                update_data = {}
                for field in ['name', 'rating', 'total_ratings', 'positive_feedback_percent']:
                    if field in seller_data and seller_data[field] is not None:
                        update_data[field] = seller_data[field]
                
                if update_data:
                    for key, value in update_data.items():
                        setattr(seller, key, value)
                    self.session.add(seller)
                    self.session.commit()
                    self.session.refresh(seller)
                
                return seller.id
            else:
                # Create new seller
                new_seller = Seller(
                    platform=seller_data['platform'],
                    seller_id=seller_data['seller_id'],
                    name=seller_data.get('name'),
                    rating=seller_data.get('rating'),
                    total_ratings=seller_data.get('total_ratings'),
                    positive_feedback_percent=seller_data.get('positive_feedback_percent')
                )
                self.session.add(new_seller)
                self.session.commit()
                self.session.refresh(new_seller)
                return new_seller.id
                
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding/updating seller: {e}")
            raise
    
    def add_product_seller(self, product_id: int, seller_id: int, price: float, shipping_price: float = 0) -> None:
        """Add or update a product-seller relationship."""
        try:
            # Check if relationship exists
            product_seller = self.session.query(ProductSeller).filter(
                ProductSeller.product_id == product_id,
                ProductSeller.seller_id == seller_id
            ).first()
            
            if product_seller:
                # Update existing relationship
                product_seller.price = price
                product_seller.shipping_price = shipping_price
                product_seller.is_available = True
                product_seller.last_checked = datetime.utcnow()
            else:
                # Create new relationship
                product_seller = ProductSeller(
                    product_id=product_id,
                    seller_id=seller_id,
                    price=price,
                    shipping_price=shipping_price,
                    is_available=True,
                    last_checked=datetime.utcnow()
                )
            
            self.session.add(product_seller)
            self.session.commit()
            self.session.refresh(product_seller)
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding/updating product-seller relationship: {e}")
            raise
    
    def add_arbitrage_opportunity(self, opportunity_data: dict) -> int:
        """
        Add a new arbitrage opportunity.
        Returns the opportunity ID.
        """
        try:
            # Check if opportunity exists
            opportunity = self.session.query(ArbitrageOpportunity).filter(
                ArbitrageOpportunity.source_product_id == opportunity_data['source_product_id'],
                ArbitrageOpportunity.target_platform == opportunity_data['target_platform']
            ).first()
            
            if opportunity:
                # Update existing opportunity
                update_data = {
                    'estimated_selling_price': opportunity_data['estimated_selling_price'],
                    'estimated_fees': opportunity_data['estimated_fees'],
                    'estimated_profit': opportunity_data['estimated_profit'],
                    'profit_margin': opportunity_data['profit_margin'],
                    'roi': opportunity_data['roi'],
                    'is_active': opportunity_data.get('is_active', True),
                    'last_checked': datetime.utcnow()
                }
                
                for key, value in update_data.items():
                    setattr(opportunity, key, value)
                
                self.session.add(opportunity)
                self.session.commit()
                self.session.refresh(opportunity)
                
                return opportunity.id
            else:
                # Create new opportunity
                new_opportunity = ArbitrageOpportunity(
                    source_product_id=opportunity_data['source_product_id'],
                    target_platform=opportunity_data['target_platform'],
                    estimated_selling_price=opportunity_data['estimated_selling_price'],
                    estimated_fees=opportunity_data['estimated_fees'],
                    estimated_profit=opportunity_data['estimated_profit'],
                    profit_margin=opportunity_data['profit_margin'],
                    roi=opportunity_data['roi'],
                    is_active=opportunity_data.get('is_active', True),
                    last_checked=datetime.utcnow()
                )
                self.session.add(new_opportunity)
                self.session.commit()
                self.session.refresh(new_opportunity)
                return new_opportunity.id
                
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding/updating arbitrage opportunity: {e}")
            raise
    
    def add_sale(self, sale_data: dict) -> int:
        """
        Add a new sale record.
        Returns the sale ID.
        """
        try:
            new_sale = SalesHistory(
                product_id=sale_data['product_id'],
                platform=sale_data['platform'],
                sale_price=sale_data['sale_price'],
                quantity=sale_data.get('quantity', 1),
                fees=sale_data.get('fees', 0),
                shipping_cost=sale_data.get('shipping_cost', 0),
                tax=sale_data.get('tax', 0),
                notes=sale_data.get('notes')
            )
            
            self.session.add(new_sale)
            self.session.commit()
            self.session.refresh(new_sale)
            return new_sale.id
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding sale record: {e}")
            raise

# Initialize the database tables
init_db()
