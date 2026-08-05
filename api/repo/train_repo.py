from supabase import AsyncClient

class TrainRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def get_train_by_number(self, train_number: str):
        response = await self.db.table("train") \
            .select("*") \
            .eq("train_number", train_number) \
            .execute()
        return response.data[0] if response.data else None
