# GoGoCar - Self Drive Car Rental Application

Refactored FastAPI application with CCAvenue payment integration and clean architecture.

## Project Structure

```
gogocar/
├── app/                    # Application code
│   ├── core/              # Configuration and logging
│   ├── db/                # Database models and session
│   ├── routes/            # API routes
│   ├── services/          # Business logic
│   ├── utils/             # Utilities
│   └── main.py            # Application entry point
├── static/                # Static files (CSS, JS, images)
│   ├── assets/           # Assets (CSS, JS, images)
│   └── images/           # Uploaded images
├── templates/             # Jinja2 templates
├── logs/                  # Application logs
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables example
└── README.md             # This file
```

## Setup

### 1. Activate Virtual Environment

```bash
cd /home/lokesh/projects/personal/develop/integration/updated-gogocars
source venv/bin/activate
```

### 2. Install Dependencies

```bash
cd gogocar
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual values
```

### 4. Initialize Database

```bash
python -c "from app.db.session import init_db; init_db()"
```

Or use Alembic migrations:
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 5. Run Application

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

## Environment Variables

See `.env.example` for all required environment variables:

- **Database**: `DATABASE_URL`
- **AWS Cognito**: `USERPOOL_ID`, `APP_CLIENT_ID`, `APP_CLIENT_SECRET`, `COGNITO_DOMAIN`
- **AWS S3**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`
- **CCAvenue**: `CCAVENUE_MERCHANT_ID`, `CCAVENUE_ACCESS_CODE`, `CCAVENUE_WORKING_KEY`

## Features

- ✅ Clean architecture with separation of concerns
- ✅ CCAvenue payment integration
- ✅ AWS Cognito authentication
- ✅ S3 file uploads
- ✅ Structured logging
- ✅ Environment-based configuration
- ✅ Type hints and documentation
- ✅ Error handling

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /auth/token` - OAuth callback
- `GET /auth/logout` - Logout
- `POST /payments/create` - Create payment
- `POST /payments/callback` - Payment callback
- `GET /payments/success` - Payment success
- `GET /payments/failure` - Payment failure
- `GET /orders/view` - View orders
- `POST /orders/checkout` - Checkout order
- `POST /orders/create` - Create order

## Documentation

- `REFACTORING_GUIDE.md` - Detailed refactoring guide
- `REFACTORING_SUMMARY.md` - Refactoring summary
- `README_REFACTORING.md` - Complete refactoring documentation

## Development

### Running in Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Add tests here when available
pytest
```

### Logging

Logs are written to `logs/app.log` in production mode.
In development mode, logs are output to console.

## Deployment

1. Set `DEBUG=False` in `.env`
2. Set `ENVIRONMENT=production` in `.env`
3. Configure production database URL
4. Configure production CCAvenue credentials
5. Run migrations
6. Start application with production server (gunicorn, etc.)

## Support

For issues or questions, refer to the documentation files or check the code comments.

## License

[Your License Here]
