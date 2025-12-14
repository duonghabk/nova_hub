# core/auth.py
from datetime import datetime
import sys
import requests
import json

SERVER_URL = "https://script.google.com/macros/s/AKfycbzje_UFPUI-__v2GDDUW84I7RDQju0LKeQch5bVooF8BAKr7-Xcptm8CdflFMaeqLnpLg/exec"
def authenticate(login_id: str, password: str, login_type: str):
   
    response = requests.post(
                SERVER_URL,
                json={'userInput': login_id, 'password': password},
                headers={'Content-Type': 'application/json'},
                timeout=15 
            )
            
    # Phân tích phản hồi JSON
    data = response.json()
    
    if data.get('success'):       
        date_iso = data.get('date')
        if date_iso:
            # Chuyển đổi từ ISO 8601 (có thể chứa Z) sang đối tượng datetime
            date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime("%Y-%m-%d")
        else:
            formatted_date = "N/A"
            
        return {
                "User_Name": data.get('user_name'),
                "Phone": data.get('phone'),
                "Company": data.get('company'),
                "Date": formatted_date,  # Ngày hết hạn
                "Permissions": data.get('permission_app'),
            }
    return None