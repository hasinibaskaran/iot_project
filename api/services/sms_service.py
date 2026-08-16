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
        # Clean phone numbers for Fast2SMS: must be 10-digit mobile numbers.
        # Remove any leading +91 or 91 country code and keep only the last 10 digits.
        cleaned_list = []
        for num in phone_numbers.split(","):
            cleaned_num = "".join(filter(str.isdigit, num.strip()))
            if len(cleaned_num) > 10:
                cleaned_num = cleaned_num[-10:]
            if cleaned_num:
                cleaned_list.append(cleaned_num)
        cleaned_phone_numbers = ",".join(cleaned_list)

        api_key = os.environ.get("FAST2SMS_API_KEY")
        if not api_key:
            logger.info(f"[MOCK SMS] Sending to {cleaned_phone_numbers}: {message}")
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
            "numbers": cleaned_phone_numbers
        }
        logger.info(f"Sending actual SMS via Fast2SMS to {cleaned_phone_numbers}: {message}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text
                except Exception:
                    pass
                logger.error(f"Fast2SMS API request failed: {str(e)} - Response: {error_body}")
                return {
                    "return": False,
                    "request_id": "failed",
                    "message": [f"API Connection error: {str(e)} - {error_body}"]
                }
            except Exception as e:
                logger.error(f"Fast2SMS API request failed: {str(e)}")
                return {
                    "return": False,
                    "request_id": "failed",
                    "message": [f"API Connection error: {str(e)}"]
                }
