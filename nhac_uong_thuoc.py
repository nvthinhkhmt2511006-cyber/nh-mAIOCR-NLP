#thinh
import os
import time
from datetime import datetime
from pydantic import BaseModel
import schedule
from google import genai
from google.genai import types
from PIL import Image

class ThongTinThuoc(BaseModel):
    ten_thuoc: str 
    lieu_luong: str 
    cac_buoi_uong: list[str] 
    gio_uong_goi_y: list[str] 
    ghi_chu: str 

class ToaThuocSmart(BaseModel):
    danh_sach_thuoc: list[ThongTinThuoc]
    so_ngay_uong: int 

def doc_toa_thuoc_bang_ai(duong_dan_anh):
    print(" Đang nhờ AI đọc toa thuốc...")
    
    os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6KKY9qRE_nOY4O29D4Na7_HuzI6AzZ0tiXqhDAa-N_ujA"
    client = genai.Client() 
    
    try:
        image = Image.open(duong_dan_anh)
    except FileNotFoundError:
        print(" Không tìm thấy file ảnh!")
        return None

    loi_dan = """
    Hãy đọc toa thuốc trong ảnh.
    Trích xuất tên thuốc, liều dùng, số ngày uống.
    Đổi các buổi (Sáng, Trưa, Chiều, Tối) thành giờ cụ thể (08:00, 12:00, 16:00, 20:00).
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image, loi_dan],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ToaThuocSmart,
            temperature=0.1 
        ),
    )
    return ToaThuocSmart.model_validate_json(response.text)

def reo_chuong_nhac_nho(ten, lieu, ghi_chu):
    print(f"\n [{datetime.now().strftime('%H:%M:%S')}] TỚI GIỜ UỐNG THUỐC!")
    print(f"Tên thuốc: {ten}")
    print(f" Liều dùng: {lieu} | Lưu ý: {ghi_chu}")
    print("-" * 40)

def cai_dat_bao_thuc(du_lieu_toa_thuoc):
    if not du_lieu_toa_thuoc:
        return

    print("\n Đã đọc xong! Lịch uống thuốc của bạn là:")
    for thuoc in du_lieu_toa_thuoc.danh_sach_thuoc:
        print(f"- {thuoc.ten_thuoc} ({thuoc.lieu_luong}): {', '.join(thuoc.gio_uong_goi_y)}")
        
        for gio in thuoc.gio_uong_goi_y:
            schedule.every().day.at(gio).do(
                reo_chuong_nhac_nho, 
                ten=thuoc.ten_thuoc, 
                lieu=thuoc.lieu_luong, 
                ghi_chu=thuoc.ghi_chu
            )
    print("\n Ứng dụng đang chạy ngầm để canh giờ...")

if __name__ == "__main__":
    anh_toa_thuoc = "don_thuoc_mau.jpg" 
    
    du_lieu = doc_toa_thuoc_bang_ai(anh_toa_thuoc)
    cai_dat_bao_thuc(du_lieu)
    
    while True:
        schedule.run_pending()
        time.sleep(1)