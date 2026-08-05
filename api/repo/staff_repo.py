from supabase import AsyncClient

class StaffRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def get_active_obhs_staff(self, trip_number: str, coach_number: str):
        response = await self.db.table("obhs_staff") \
            .select("name, phone_number") \
            .eq("trip_number", trip_number) \
            .eq("is_active", True) \
            .or_(f"coach_number.eq.{coach_number},coach_number.eq.ALL") \
            .execute()
        return response.data
