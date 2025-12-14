# core/auth.py
import datetime


def mock_authenticate(login_id: str, password: str, login_type: str):
    """
    Hàm giả lập xác thực người dùng.
    Kiểm tra thông tin đăng nhập được hardcode.
    """
    # Trong ứng dụng thực tế, bạn sẽ tra cứu người dùng trong cơ sở dữ liệu
    # dựa trên số điện thoại hoặc tên người dùng.
    is_user_ok = (
        login_type == "username" and login_id == "admin" and password == "123"
    )
    is_phone_ok = (
        login_type == "phone" and login_id == "12345" and password == "123"
    )

    if is_user_ok or is_phone_ok:
        return {
            "User_Name": "admin",
            "Phone": "12345",
            "Company": "nova",
            "Date": "2027-12-01",  # Ngày hết hạn
            "Permissions": ["nova_prompt_maker", "nova_capcut_tool","nova_veo3_downloader"],
        }
    return None