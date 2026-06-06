#Thinh
import streamlit as st
from pydantic import BaseModel
from google import genai
from google.genai import types
from PIL import Image
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class ThongTinThuoc(BaseModel):
    ten_thuoc: str 
    lieu_luong: str 
    cac_buoi_uong: list[str] 
    gio_uong_goi_y: list[str] 
    ghi_chu: str 

class ToaThuocSmart(BaseModel):
    danh_sach_thuoc: list[ThongTinThuoc]
    so_ngay_uong: int 


def gui_email(email_nhan, tieu_de, noi_dung):
    try:
        
        email_gui = st.secrets["thinhai20077@gmail.com"]
        mat_khau_gui = st.secrets["Thinhobito1@"]
        
        msg = MIMEMultipart()
        msg['From'] = email_gui
        msg['To'] = email_nhan
        msg['Subject'] = tieu_de
        msg.attach(MIMEText(noi_dung, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_gui, mat_khau_gui)
        server.sendmail(email_gui, email_nhan, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Lỗi gửi email: {e}")
        return False

def vong_lap_canh_gio():
    import schedule
    while True:
        schedule.run_pending()
        time.sleep(1)

if "luong_chay_ngam" not in st.session_state:
    import schedule
    st.session_state.luong_chay_ngam = True
    t = threading.Thread(target=vong_lap_canh_gio, daemon=True)
    t.start()

def cai_dat_hen_gio(du_lieu_toa, email_nhan):
    import schedule
    schedule.clear()
    
    for thuoc in du_lieu_toa.danh_sach_thuoc:
        for gio in thuoc.gio_uong_goi_y:
            tieu_de = f"ĐẾN GIỜ UỐNG THUỐC: {thuoc.ten_thuoc}"
            noi_dung = f"Liều dùng: {thuoc.lieu_luong}\nGhi chú: {thuoc.ghi_chu}"
            schedule.every().day.at(gio).do(
                gui_email,
                email_nhan=email_nhan,
                tieu_de=tieu_de,
                noi_dung=noi_dung
            )
    st.toast("Đã kích hoạt lịch nhắc nhở qua Gmail thành công!")


def doc_toa_thuoc_bang_ai(file_anh):
    client = genai.Client(api_key="AQ.Ab8RN6Ib7G97w9qqsMcWTPtj2-UGwy9zLPGcD4OwdSy6QoDAKQ") 
    
    image = Image.open(file_anh)
    loi_dan = """
    Hãy đọc thật kỹ toa thuốc trong ảnh này.
    Trích xuất chính xác: tên thuốc, liều dùng, số ngày uống, ghi chú (nếu có).
    Đổi các buổi uống (Sáng, Trưa, Chiều, Tối) thành giờ cụ thể gợi ý tương ứng (08:00, 12:00, 16:00, 20:00).
    Trả về dữ liệu dưới dạng JSON nghiêm ngặt tuân theo cấu trúc ToaThuocSmart.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[image, loi_dan],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ToaThuocSmart,
            temperature=0.1 
        ),
    )
    return ToaThuocSmart.model_validate_json(response.text)


st.set_page_config(page_title="Trợ Lý Nhắc Thuốc")
st.title("Trợ Lý Đọc Toa Thuốc & Nhắc Nhở")


email_nguoi_dung = st.text_input("Nhập Gmail của bạn để nhận lịch nhắc nhở:")

file_tai_len = st.file_uploader("Tải ảnh toa thuốc của bạn lên đây...", type=["jpg", "jpeg", "png"])

if file_tai_len is not None:
    st.image(file_tai_len, caption="Ảnh đã tải lên", use_container_width=True)
    
    if st.button("Phân tích & Bật báo thức"):
        if not email_nguoi_dung:
            st.error("Vui lòng nhập Gmail của bạn trước khi tiếp tục.")
        else:
            with st.spinner("AI đang quét đơn thuốc và lên lịch hẹn giờ..."):
                try:
                    du_lieu = doc_toa_thuoc_bang_ai(file_tai_len)
                    if du_lieu:
                        st.success(f"Đơn thuốc dùng trong {du_lieu.so_ngay_uong} ngày")
                        
                        noi_dung_tong_hop = f"Lịch uống thuốc tổng hợp của bạn ({du_lieu.so_ngay_uong} ngày):\n\n"
                        for thuoc in du_lieu.danh_sach_thuoc:
                            noi_dung_tong_hop += f"- Thuốc: {thuoc.ten_thuoc}\n  Liều dùng: {thuoc.lieu_luong}\n  Giờ nhắc: {', '.join(thuoc.gio_uong_goi_y)}\n  Ghi chú: {thuoc.ghi_chu}\n\n"
                        
                        
                        gui_email(email_nguoi_dung, "Tổng hợp lịch uống thuốc", noi_dung_tong_hop)
                        
                        
                        cai_dat_hen_gio(du_lieu, email_nguoi_dung)
                        
                        for thuoc in du_lieu.danh_sach_thuoc:
                            with st.expander(thuoc.ten_thuoc):
                                st.write(f"**Liều dùng:** {thuoc.lieu_luong}")
                                st.write(f"**Giờ uống báo thức:** {', '.join(thuoc.gio_uong_goi_y)}")
                                if thuoc.ghi_chu: 
                                    st.info(f"**Ghi chú:** {thuoc.ghi_chu}")
                except Exception as e:
                    st.error(f"Lỗi: Hãy chắc chắn bạn đã cấu hình Email Hệ Thống trong Secrets. Chi tiết lỗi: {e}")