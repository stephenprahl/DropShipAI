# Super Arbitrage - AI-Powered Dropshipping Automation

An autonomous system for identifying and capitalizing on dropshipping arbitrage opportunities using AI. Super Arbitrage helps you find profitable products across multiple marketplaces, track price changes, and manage your online arbitrage business efficiently.

## 🚀 Features

- **Multi-Marketplace Support**: Connect to Amazon, eBay, Walmart, and more
- **Automated Price Tracking**: Monitor price changes and stock levels in real-time
- **Profit Calculation**: Automatic calculation of fees, shipping costs, and profit margins
- **Smart Alerts**: Get notified of profitable opportunities and price drops
- **User Management**: Role-based access control for teams
- **API Access**: Full REST API for integration with other tools
- **Modern Dashboard**: Intuitive web interface for managing your arbitrage business
- **Background Processing**: Asynchronous task processing with Celery
- **Scalable Architecture**: Built with Flask and SQLAlchemy for high performance

## 📦 Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+ (or use [Neon](https://neon.tech/) for a managed solution)
- Redis (for task queue)
- Node.js 16+ (for frontend assets)

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/super-arb.git
   cd super-arb
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install frontend dependencies:
   ```bash
   npm install
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your configuration.

6. Initialize the database:
   ```bash
   flask db upgrade
   flask init-db
   ```

7. Run the development server:
   ```bash
   flask run
   ```

8. In a separate terminal, start the Celery worker:
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

9. Access the application at `http://localhost:5000`

## 🗄️ Database Setup

Super Arbitrage uses PostgreSQL as its primary database. You can use a local PostgreSQL instance or a cloud provider like [Neon](https://neon.tech/), [Supabase](https://supabase.com/), or [Render](https://render.com/).

1. Create a new database
2. Update your `.env` file with the database connection string:
   ```env
   DATABASE_URL=postgresql://username:password@hostname:port/dbname
   ```
3. Run migrations:
   ```bash
   flask db upgrade
   ```

## 🔐 Authentication

Super Arbitrage uses Flask-Login for authentication. The first user to register will be granted admin privileges.

### Creating an Admin User

```bash
flask create-user --email admin@example.com --username admin --password yourpassword --admin
```

## 🌐 API Documentation

API documentation is available at `/api/docs` when running the development server. The API uses JWT for authentication.

### Generating API Keys

1. Log in to the web interface
2. Go to Account Settings > API Keys
3. Click "Generate New API Key"
4. Copy and securely store your API key

## 🔄 Background Tasks

Super Arbitrage uses Celery with Redis as a message broker for background tasks like:

- Price scraping
- Opportunity detection
- Notification sending
- Report generation

### Starting the Celery Worker

```bash
celery -A app.celery worker --loglevel=info
```

### Monitoring with Flower

Flower is a web-based tool for monitoring Celery workers:

```bash
celery -A app.celery flower --port=5555
```

Access the Flower dashboard at `http://localhost:5555`

## 🧪 Testing

Run the test suite with:

```bash
pytest
```

## 🚀 Deployment

### Production Deployment

For production deployment, we recommend using:

- **Web Server**: Gunicorn or uWSGI
- **Reverse Proxy**: Nginx or Apache
- **Process Manager**: systemd, Supervisor, or Docker
- **Database**: PostgreSQL with connection pooling (PgBouncer)
- **Caching**: Redis
- **Background Tasks**: Celery with Redis/RabbitMQ

#### Example Gunicorn Command

```bash
gunicorn -w 4 -b 127.0.0.1:8000 "app:create_app()"
```

#### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/super-arb/app/static;
        expires 30d;
    }
}
```

## 📚 Documentation

For detailed documentation, please visit our [documentation site](https://super-arb.readthedocs.io/).

## 🤝 Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) before submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📬 Contact

For support or questions, please open an issue or contact us at support@superarb.com
5. The database tables will be automatically created when you first run the application

### Configuration

Copy the `.env.example` file to `.env` and fill in your API keys and configuration:

```bash
cp .env.example .env
```

Edit the `.env` file with your actual API keys and configuration values.
3. Configure your API keys in `.env` file
4. Run the main script:
   ```bash
   python src/main.py
   ```

## 📂 Project Structure

```
super-arb/
├── src/                    # Source code
│   ├── scraping/          # Web scraping modules
│   ├── analysis/          # Data analysis and AI models
│   ├── automation/        # Automation scripts
│   └── utils/             # Utility functions
├── data/                  # Data storage
├── config/                # Configuration files
├── .env                  # Environment variables
└── requirements.txt      # Python dependencies
```

## 🔑 Environment Variables

Create a `.env` file with your API keys:

```
# Amazon API
AMAZON_ACCESS_KEY=your_access_key
AMAZON_SECRET_KEY=your_secret_key
AMAZON_ASSOC_TAG=your_assoc_tag

# eBay API
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id

# AliExpress API
ALIEXPRESS_API_KEY=your_api_key
```

## 🤖 Usage

Run the main script:

```bash
python src/main.py
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
