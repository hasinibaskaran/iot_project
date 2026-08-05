from supabase import AsyncClient

class AlertLogRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def create_log(self, log_data: dict):
        response = await self.db.table("alert_log").insert(log_data).execute()
        return response.data
