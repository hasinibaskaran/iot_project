from fastapi import APIRouter, Depends
from supabase import AsyncClient
from api.database import get_supabase
from api.schemas.alert import AlertRequest, AlertResponse
from api.services.alert_service import AlertService
from api.security import verify_api_key

router = APIRouter(
    prefix="/api",
    tags=["Alerts"],
    dependencies=[Depends(verify_api_key)]
)

@router.post("/alert", response_model=AlertResponse)
async def alert_dispatch(
    request: AlertRequest,
    db: AsyncClient = Depends(get_supabase)
):
    """
    Receives IoT coach sanitation alerts and dispatches SMS notifications
    to assigned active staff or fallbacks.
    """
    alert_service = AlertService(db)
    return await alert_service.process_alert(request)
