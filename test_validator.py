from src.db.session import SessionLocal

from src.services.metrics_service import (
    get_dashboard_metrics
)

db = SessionLocal()

print(

    get_dashboard_metrics(
        db
    )
)