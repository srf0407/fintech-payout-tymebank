from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
from contextlib import asynccontextmanager
from .core.config import settings
from .core.logging import configure_logging, logger, set_correlation_id, get_correlation_id
from .db.session import engine, Base
from .api.routes import auth, payouts, webhooks
from .services.webhook_callback_service import webhook_callback_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging()
    logger.info("Starting Fintech Payouts API")
    
    # Register webhook callback with mock payment provider
    webhook_callback_service.register_webhook_callback()
    logger.info("Webhook callback registered with mock payment provider")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fintech Payouts API")

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins + ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to every request and log request/response"""
    
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    set_correlation_id(correlation_id)
    
    start_time = time.time()
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url.path),
        query_params=str(request.url.query) if request.url.query else None,
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None
    )
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            "request_completed",
            method=request.method,
            url=str(request.url.path),
            status_code=response.status_code,
            process_time=round(process_time, 4)
        )
        
        response.headers["x-correlation-id"] = correlation_id
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "request_failed", 
            method=request.method,
            url=str(request.url.path),
            error=str(e),
            error_type=type(e).__name__,
            process_time=round(process_time, 4)
        )
        raise

app.include_router(auth.router)
app.include_router(payouts.router)
app.include_router(webhooks.router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("health_check_requested")
    return {"status": "healthy", "correlation_id": get_correlation_id()}

