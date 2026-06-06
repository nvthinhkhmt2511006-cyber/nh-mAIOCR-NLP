import streamlit as st
from pydantic import BaseModel
import base64
from openai import OpenAI
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule

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
        email_gui = st.secrets["EMAIL_HE_THONG"]
        mat_khau_gui = st.secrets["MAT_KHAU_HE_THONG"]
        
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

def vong_lap_canh_gio(bo_lenh_lich):
    while True:
        bo_lenh_lich.run_pending()
        time.sleep(1)

if "bo_lenh_lich" not in st.session_state:
    st.session_state.bo_lenh_lich = schedule.Scheduler()
    t = threading.Thread(target=vong_lap_canh_gio, args=(st.session_state.bo_lenh_lich,), daemon=True)
    t.start()

def cai_dat_hen_gio(du_lieu_toa, email_nhan):
    st.session_state.bo_lenh_lich.clear()
    for thuoc in du_lieu_toa.danh_sach_thuoc:
        for gio in thuoc.gio_uong_goi_y:
            tieu_de = f"ĐẾN GIỜ UỐNG THUỐC: {thuoc.ten_thuoc}"
            noi_dung = f"Liều dùng: {thuoc.lieu_luong}\nGhi chú: {thuoc.ghi_chu}"
            st.session_state.bo_lenh_lich.every().day.at(gio).do(
                gui_email,
                email_nhan=email_nhan,
                tieu_de=tieu_de,
                noi_dung=noi_dung
            )
    st.toast("Đã kích hoạt lịch nhắc nhở qua Gmail thành công!")

def doc_toa_thuoc_bang_ai(van_ban_toa):
    api_key_cua_ban = st.secrets["SAMBANOVA_API_KEY"]
    client = OpenAI(
        api_key=api_key_cua_ban,
        base_url="https://api.sambanova.ai/v1",
    )
    
    loi_dan = """
    Hãy phân tích đoạn văn bản đơn thuốc sau đây.
    Trích xuất chính xác: tên thuốc, liều dùng, số ngày uống, ghi chú (nếu có).
    Đổi các buổi uống (Sáng, Trưa, Chiều, Tối) thành giờ cụ thể gợi ý tương ứng (08:00, 12:00, 16:00, 20:00).
    TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON (không giải thích thêm) theo cấu trúc mẫu sau:
    {
      "danh_sach_thuoc": [
        {
          "ten_thuoc": "Tên",
          "lieu_luong": "Liều",
          "cac_buoi_uong": ["Sáng", "Chiều"],
          "gio_uong_goi_y": ["08:00", "16:00"],
          "ghi_chu": "Sau ăn"
        }
      ],
      "so_ngay_uong": 5
    }
    """

    response = client.chat.completions.create(
        model="llama3.1-8b", 
        messages=[
            {"role": "system", "content": loi_dan},
            {"role": "user", "content": van_ban_toa}
        ],
        temperature=0.1
    )
    
    ket_qua = response.choices[0].message.content
    if "```json" in ket_qua:
        ket_qua = ket_qua.split("```json")[1].split("```")[0].strip()
    elif "```" in ket_qua:
        ket_qua = ket_qua.split("```")[1].split("```")[0].strip()
        
    return ToaThuocSmart.model_validate_json(ket_qua)

st.set_page_config(page_title="Trợ Lý Nhắc Thuốc")
st.title("Trợ Lý Phân Tích Toa Thuốc & Nhắc Nhở")

email_nguoi_dung = st.text_input("Nhập Gmail của bạn để nhận lịch nhắc nhở:")
van_ban_nhap = st.text_area("Dán nội dung chữ của đơn thuốc vào đây...", height=150)

if van_ban_nhap:
    if st.button("Phân tích & Bật báo thức"):
        if not email_nguoi_dung:
            st.error("Vui lòng nhập Gmail của bạn trước khi tiếp tục.")
        else:
            with st.spinner("SambaNova Llama 3.1 đang xử lý dữ liệu..."):
                try:
                    du_lieu = doc_toa_thuoc_bang_ai(van_ban_nhap)
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
                    st.error(f"Lỗi: {e}")
