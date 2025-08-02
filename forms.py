"""Form classes for the Super Arbitrage application."""
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                    TextAreaField, SelectField, DecimalField, IntegerField,
                    DateField, DateTimeField, HiddenField, FileField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Optional,
                               NumberRange, URL, ValidationError, InputRequired)
from wtforms.widgets import PasswordInput
from .models import User, Marketplace
from .utils import validate_url

class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ], render_kw={"placeholder": "Enter your email"})
    
    password = PasswordField('Password', validators=[
        DataRequired()
    ], render_kw={"placeholder": "Enter your password"})
    
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=4, max=25)
    ], render_kw={"placeholder": "Choose a username"})
    
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ], render_kw={"placeholder": "Enter your email"})
    
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ], render_kw={"placeholder": "Create a strong password"})
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ], render_kw={"placeholder": "Confirm your password"})
    
    agree_terms = BooleanField('I agree to the Terms of Service and Privacy Policy', 
                             validators=[DataRequired()])
    
    submit = SubmitField('Create Account')
    
    def validate_username(self, username):
        """Check if username is already taken."""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        """Check if email is already registered."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class ResetPasswordRequestForm(FlaskForm):
    """Request password reset form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ], render_kw={"placeholder": "Enter your email address"})
    
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    """Reset password form."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ], render_kw={"placeholder": "Enter a new password"})
    
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ], render_kw={"placeholder": "Confirm your new password"})
    
    submit = SubmitField('Reset Password')


class ProductForm(FlaskForm):
    """Add/Edit product form."""
    name = StringField('Product Name', validators=[
        DataRequired(),
        Length(max=255)
    ], render_kw={"placeholder": "Enter product name"})
    
    upc = StringField('UPC', validators=[
        Optional(),
        Length(min=12, max=13, message='UPC must be 12 or 13 digits')
    ], render_kw={"placeholder": "12 or 13 digit UPC code"})
    
    asin = StringField('ASIN', validators=[
        Optional(),
        Length(min=10, max=10, message='ASIN must be 10 characters')
    ], render_kw={"placeholder": "Amazon Standard Identification Number"})
    
    brand = StringField('Brand', validators=[
        Optional(),
        Length(max=100)
    ], render_kw={"placeholder": "Brand name"})
    
    category = StringField('Category', validators=[
        Optional(),
        Length(max=100)
    ], render_kw={"placeholder": "Product category"})
    
    image_url = StringField('Image URL', validators=[
        Optional(),
        URL(),
        Length(max=512)
    ], render_kw={"placeholder": "URL to product image"})
    
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=2000)
    ], render_kw={"rows": 4, "placeholder": "Product description"})
    
    weight = DecimalField('Weight (g)', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2, render_kw={"placeholder": "Weight in grams"})
    
    dimensions = StringField('Dimensions (LxWxH cm)', validators=[
        Optional(),
        Length(max=50)
    ], render_kw={"placeholder": "e.g., 15.5x10.2x5.8"})
    
    submit = SubmitField('Save Product')
    
    def validate_image_url(self, field):
        """Validate image URL."""
        if field.data and not validate_url(field.data):
            raise ValidationError('Invalid URL')


class MarketplaceCredentialsForm(FlaskForm):
    """Marketplace API credentials form."""
    marketplace_id = SelectField('Marketplace', coerce=int, validators=[
        DataRequired()
    ])
    
    api_key = StringField('API Key', validators=[
        DataRequired(),
        Length(max=255)
    ], render_kw={"placeholder": "Your API key"})
    
    api_secret = PasswordField('API Secret', validators=[
        DataRequired(),
        Length(max=255)
    ], render_kw={"placeholder": "Your API secret"})
    
    seller_id = StringField('Seller ID', validators=[
        Optional(),
        Length(max=100)
    ], render_kw={"placeholder": "Your seller/marketplace ID"})
    
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Credentials')
    
    def __init__(self, *args, **kwargs):
        super(MarketplaceCredentialsForm, self).__init__(*args, **kwargs)
        self.marketplace_id.choices = [
            (m.id, m.name) for m in Marketplace.query.order_by('name').all()
        ]


class OpportunityFilterForm(FlaskForm):
    """Filter opportunities form."""
    status = SelectField('Status', choices=[
        ('all', 'All Statuses'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('sold', 'Sold'),
        ('removed', 'Removed')
    ], default='active')
    
    source_marketplace_id = SelectField('Source Marketplace', coerce=int, validators=[
        Optional()
    ], choices=[])
    
    target_marketplace_id = SelectField('Target Marketplace', coerce=int, validators=[
        Optional()
    ], choices=[])
    
    min_profit = DecimalField('Min Profit', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)
    
    min_margin = DecimalField('Min Margin %', validators=[
        Optional(),
        NumberRange(min=0, max=1000)
    ], places=2)
    
    sort_by = SelectField('Sort By', choices=[
        ('profit', 'Highest Profit'),
        ('margin', 'Highest Margin'),
        ('created', 'Newest First'),
        ('updated', 'Recently Updated')
    ], default='profit')
    
    submit = SubmitField('Apply Filters')
    
    def __init__(self, *args, **kwargs):
        super(OpportunityFilterForm, self).__init__(*args, **kwargs)
        # Populate marketplace choices
        marketplaces = Marketplace.query.order_by('name').all()
        marketplace_choices = [(0, 'All Marketplaces')] + [(m.id, m.name) for m in marketplaces]
        self.source_marketplace_id.choices = marketplace_choices
        self.target_marketplace_id.choices = marketplace_choices


class NotificationSettingsForm(FlaskForm):
    """Notification settings form."""
    email_notifications = BooleanField('Email Notifications', default=True)
    push_notifications = BooleanField('Push Notifications', default=False)
    
    # Alert preferences
    alert_profit = BooleanField('New profitable opportunities', default=True)
    alert_price_drop = BooleanField('Price drops', default=True)
    alert_competition = BooleanField('New competition', default=False)
    alert_newsletter = BooleanField('Weekly newsletter', default=True)
    
    # Notification frequency
    frequency = SelectField('Email Frequency', choices=[
        ('immediate', 'Immediate'),
        ('hourly', 'Hourly Digest'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest')
    ], default='immediate')
    
    submit = SubmitField('Save Settings')


class ImportProductsForm(FlaskForm):
    """Import products form."""
    marketplace_id = SelectField('Marketplace', coerce=int, validators=[
        DataRequired()
    ])
    
    import_file = FileField('CSV File', validators=[
        DataRequired()
    ])
    
    update_existing = BooleanField('Update existing products', default=True)
    
    submit = SubmitField('Import Products')
    
    def __init__(self, *args, **kwargs):
        super(ImportProductsForm, self).__init__(*args, **kwargs)
        self.marketplace_id.choices = [
            (m.id, m.name) for m in Marketplace.query.order_by('name').all()
        ]


class APIKeyForm(FlaskForm):
    """API key generation form."""
    name = StringField('Key Name', validators=[
        DataRequired(),
        Length(max=100)
    ], render_kw={"placeholder": "e.g., Mobile App, Integration X"})
    
    expires_in = SelectField('Expires In', choices=[
        (str(3600), '1 Hour'),
        (str(86400), '1 Day'),
        (str(604800), '1 Week'),
        (str(2592000), '1 Month'),
        ('0', 'Never')
    ], default=str(2592000))
    
    permissions = SelectField('Permissions', choices=[
        ('read', 'Read Only'),
        ('read_write', 'Read & Write'),
        ('admin', 'Admin')
    ], default='read')
    
    submit = SubmitField('Generate API Key')
