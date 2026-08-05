import logging
from supabase import AsyncClient
from api.repo.trip_repo import TripRepository
from api.repo.staff_repo import StaffRepository
from api.repo.route_repo import RouteRepository
from api.repo.device_repo import DeviceRepository
from api.repo.alert_log_repo import AlertLogRepository
from api.repo.train_repo import TrainRepository
from api.schemas.alert import AlertRequest, AlertResponse, SmsResponseDetail
from api.services.sms_service import SmsService
from fastapi import HTTPException, status

logger = logging.getLogger("smart_sanitation_backend")

class AlertService:
    def __init__(self, db: AsyncClient):
        self.db = db
        self.trip_repo = TripRepository(db)
        self.staff_repo = StaffRepository(db)
        self.route_repo = RouteRepository(db)
        self.device_repo = DeviceRepository(db)
        self.log_repo = AlertLogRepository(db)
        self.train_repo = TrainRepository(db)

    async def process_alert(self, request: AlertRequest) -> AlertResponse:
        trip = await self.trip_repo.get_trip_by_number(request.trip_number)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {request.trip_number} not found"
            )

        # Get train details to retrieve train_name from repo
        train = await self.train_repo.get_train_by_number(request.train_number)
        train_name = train["train_name"] if train else "Unknown Train"

        # 1. Look up active OBHS staff
        staff_members = await self.staff_repo.get_active_obhs_staff(request.trip_number, request.coach_number)
        
        dispatched_to_type = "OBHS_STAFF"
        recipients = []

        if staff_members:
            recipients = [{"name": s["name"], "phone": s["phone_number"]} for s in staff_members]
            dispatched_to = f"OBHS Staff ({', '.join([s['name'] for s in staff_members])})"
            message = (
                f"Urgent: Sanitation requested on Train {request.train_number} ({train_name}), "
                f"Coach {request.coach_number}. Please attend immediately. [Alert Time: {request.time}]"
            )
        else:
            # 2. Fallback to next station manager
            manager = await self.route_repo.get_station_manager(request.next_station_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"No active OBHS staff found and station manager info "
                        f"missing for station {request.next_station_id}"
                    )
                )
            
            recipients = [{"name": f"Station Manager ({manager['station_name']})", "phone": manager["manager_phone"]}]
            dispatched_to = f"Station Manager ({manager['station_name']})"
            dispatched_to_type = "STATION_MANAGER"
            message = (
                f"Sanitation Alert: Train {request.train_number} ({train_name}) Coach {request.coach_number} "
                f"requires sanitation. OBHS team offline. Please arrange station cleanup at {manager['station_name']}."
            )

        # 3. Send SMS
        phone_numbers = ",".join([r["phone"] for r in recipients])
        sms_res = await SmsService.send_sms(message, phone_numbers)

        # 4. Log alert
        device_id = await self.device_repo.get_device_by_train(request.train_number)
        sms_status = "DELIVERED" if sms_res.get("return") is True else "FAILED"

        for recipient in recipients:
            try:
                log_data = {
                    "device_id": device_id,
                    "train_number": request.train_number,
                    "trip_number": request.trip_number,
                    "coach_number": request.coach_number,
                    "last_station_id": request.last_station_id,
                    "next_station_id": request.next_station_id,
                    "dispatched_to_type": dispatched_to_type,
                    "recipient_phone": recipient["phone"],
                    "sms_status": sms_status
                }
                await self.log_repo.create_log(log_data)
            except Exception as e:
                logger.error(f"Failed to write log row into alert_log: {str(e)}")

        return AlertResponse(
            success=True,
            dispatched_to=dispatched_to,
            sms_response=SmsResponseDetail(
                return_val=sms_res.get("return", False),
                request_id=sms_res.get("request_id", ""),
                message=sms_res.get("message", [])
            )
        )
