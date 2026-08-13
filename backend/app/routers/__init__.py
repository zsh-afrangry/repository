from .bill import router as bill_router
from .calendar import router as calendar_router
from .dashboard import router as dashboard_router
from .tag import router as tag_router
from .weather import router as weather_router

__all__ = ["bill_router", "calendar_router", "dashboard_router", "tag_router", "weather_router"]
