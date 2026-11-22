import logging
import sys
from app.core.config import settings

def setup_logging():
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Custom formatter that ensures clean consistent log formatting
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    
    # Quiet down overly noisy external libraries if needed
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger("personal_ai.backend")
