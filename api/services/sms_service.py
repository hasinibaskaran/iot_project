import os
import time
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger("smart_sanitation_backend")

class SmsService:
    @staticmethod
    async def send_sms(message: str, phone_numbers: str) -> Dict[str, Any]:
        """
        Sends an SMS via Fast2SMS bulkV2 Quick SMS API.
        If FAST2SMS_API_KEY is not configured, runs in mock sandbox mode.
        """
        api_key = os.environ.get("FAST2SMS_API_KEY")
        if not api_key:
            logger.info(f"[MOCK SMS] Sending to {phone_numbers}: {message}")
            return {
                "return": True,
                "request_id": f"mock_req_{int(time.time())}",
                "message": ["SMS mock sent successfully."]
            }
        
        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "route": "q",
            "message": message,
            "numbers": phone_numbers
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Fast2SMS API request failed: {str(e)}")
                return {
                    "return": False,
                    "request_id": "failed",
                    "message": [f"API Connection error: {str(e)}"]
                }
