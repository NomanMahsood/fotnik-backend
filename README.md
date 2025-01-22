# Fotnik Backend API

FastAPI-based backend for the Fotnik application, supporting both HTTP requests and WebSocket connections.

## Project Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py         # Configuration settings
│   ├── websockets/
│   │   ├── connection_manager.py  # WebSocket connection handling
│   │   └── routes.py         # WebSocket routes
│   └── __init__.py
├── main.py                   # Main application entry point
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the backend directory with your configuration:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fotnik
```

## Running the Application

Start the development server:
```bash
python main.py
```

The API will be available at `http://localhost:8010`
- API Documentation: `http://localhost:8010/docs`
- WebSocket endpoint: `ws://localhost:8010/ws/{client_id}`

## API Features

- RESTful endpoints under `/api/v1`
- Real-time WebSocket communication
- CORS support for frontend integration
- PostgreSQL database integration
- Environment-based configuration 

# fotnik-backend


