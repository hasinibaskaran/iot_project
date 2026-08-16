import os
import time
import logging
import httpx
import asyncio
from typing import Dict, Any

logger = logging.getLogger("smart_sanitation_backend")

class SmsService:
    @staticmethod
    async def send_sms(message: str, phone_numbers: str) -> Dict[str, Any]:
        """
        Sends an SMS via Twilio Messages API.
        If TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_FROM_NUMBER are not configured,
        runs in mock sandbox mode.
        """
        # Clean phone numbers to standard E.164 format for Twilio (e.g. +918489422354)
        cleaned_list = []
        for num in phone_numbers.split(","):
            cleaned_num = "".join(c for c in num.strip() if c.isdigit() or c == "+")
            if not cleaned_num.startswith("+"):
                if len(cleaned_num) == 10:
                    cleaned_num = "+91" + cleaned_num
                else:
                    cleaned_num = "+" + cleaned_num
            if cleaned_num:
                cleaned_list.append(cleaned_num)

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            logger.info(f"[MOCK SMS] Sending to {','.join(cleaned_list)}: {message}")
            return {
                "return": True,
                "request_id": f"mock_req_{int(time.time())}",
                "message": ["SMS mock sent successfully."]
            }
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        async def send_to_one(client: httpx.AsyncClient, to_number: str) -> Dict[str, Any]:
            data = {
                "To": to_number,
                "From": from_number,
                "Body": message
            }
            logger.info(f"Sending actual SMS via Twilio to {to_number}: {message}")
            try:
                response = await client.post(url, data=data, auth=(account_sid, auth_token), timeout=10.0)
                response.raise_for_status()
                res_json = response.json()
                return {
                    "success": True,
                    "request_id": res_json.get("sid", ""),
                    "message": "Sent successfully"
                }
            except httpx.HTTPStatusError as e:
                error_body = ""
                try:
                    error_body = e.response.text
                except Exception:
                    pass
                logger.error(f"Twilio API request failed for {to_number}: {str(e)} - Response: {error_body}")
                return {
                    "success": False,
                    "error": f"API Connection error: {str(e)} - {error_body}"
                }
            except Exception as e:
                logger.error(f"Twilio API request failed for {to_number}: {str(e)}")
                return {
                    "success": False,
                    "error": f"API Connection error: {str(e)}"
                }

        async with httpx.AsyncClient() as client:
            tasks = [send_to_one(client, num) for num in cleaned_list]
            results = await asyncio.gather(*tasks)
            
        all_success = all(r["success"] for r in results)
        request_ids = [r.get("request_id") for r in results if r["success"]]
        errors = [r.get("error") for r in results if not r["success"]]
        
        return {
            "return": all_success,
            "request_id": ",".join(request_ids) if request_ids else "failed",
            "message": ["SMS sent successfully."] if all_success else errors
        }
