#thinh huyen khiem khanh
import streamlit as st
from pydantic import BaseModel, Field
from typing import Optional, List
import base64
from openai import OpenAI
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import re

class ThongTinThuoc(BaseModel):
    ten_thuoc: str = Field(default="")
    lieu_luong: Optional[str] = Field(default="")
    cac_buoi_uong: List[str] = Field(default_factory=list)
    gio_uong_goi_y: List[str] = Field(default_factory=list)
    ghi_chu: Optional[str] = Field(default="")

class ToaThuocSmart(BaseModel):
    danh_sach_thuoc: List[ThongTinThuoc] = Field(default_factory=list)
    so_ngay_uong: int = Field(default=1)

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
            if not gio:
                continue
            gio_chuan = str(gio).strip()
            match = re.search(r'(\d{1,2}):(\d{2})', gio_chuan)
            if match:
                h, m = match.groups()
                gio_chuan = f"{int(h):02d}:{int(m):02d}"
            else:
                gio_chuan = "08:00"
                
            try:
                tieu_de = f"ĐẾN GIỜ UỐNG THUỐC: {thuoc.ten_thuoc}"
                noi_dung = f"Liều dùng: {thuoc.lieu_luong or ''}\nGhi chú: {thuoc.ghi_chu or ''}"
                st.session_state.bo_lenh_lich.every().day.at(gio_chuan).do(
                    gui_email,
                    email_nhan=email_nhan,
                    tieu_de=tieu_de,
                    noi_dung=noi_dung
                )
            except Exception as e:
                print(f"Bỏ qua giờ lỗi: {e}")
                
    st.toast("Đã kích hoạt lịch nhắc nhở qua Gmail thành công!")

def encode_image(file_anh):
    return base64.b64encode(file_anh.getvalue()).decode('utf-8')

def doc_toa_thuoc_bang_ai(file_anh):
    api_key_cua_ban = st.secrets["SAMBANOVA_API_KEY"]
    client = OpenAI(
        api_key=api_key_cua_ban,
        base_url="https://api.sambanova.ai/v1",
    )
    base64_image = encode_image(file_anh)
    
    loi_dan = """
    Hãy đọc thật kỹ toa thuốc trong ảnh này.
    Trích xuất chính xác: tên thuốc, liều dùng, số ngày uống, ghi chú (nếu có).
    Đổi các buổi uống (Sáng, Trưa, Chiều, Tối) thành giờ cụ thể gợi ý chuẩn 24h (BẮT BUỘC ĐỊNH DẠNG HH:MM, ví dụ: "08:00", "12:00", "16:00", "20:00").
    TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON. 
    LƯU Ý QUAN TRỌNG:
    - Nếu trường văn bản nào không có thông tin hoặc trống, hãy điền chuỗi rỗng "". Tuyệt đối KHÔNG sử dụng null.
    - Riêng trường "so_ngay_uong" BẮT BUỘC phải là một SỐ NGUYÊN (ví dụ: 5, 7). Nếu đơn thuốc không ghi số ngày, hãy trả về số 1. TUYỆT ĐỐI KHÔNG trả về chuỗi rỗng "" hoặc null cho trường này.
    Cấu trúc mẫu:
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

    for luot_thu in range(3):
        try:
            response = client.chat.completions.create(
                model="Llama-4-Maverick-17B-128E-Instruct", 
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": loi_dan},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1
            )
            
            ket_qua = response.choices[0].message.content
            if "```json" in ket_qua:
                ket_qua = ket_qua.split("```json")[1].split("```")[0].strip()
            elif "```" in ket_qua:
                ket_qua = ket_qua.split("```")[1].split("```")[0].strip()
                
            return ToaThuocSmart.model_validate_json(ket_qua)
            
        except Exception as e:
            if "429" in str(e) and luot_thu < 2:
                time.sleep(6)
                continue
            raise e

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
            with st.spinner("SambaNova AI đang phân tích đơn thuốc..."):
                try:
                    du_lieu = doc_toa_thuoc_bang_ai(file_tai_len)
                    if du_lieu:
                        st.success(f"Đơn thuốc dùng trong {du_lieu.so_ngay_uong} ngày")
                        noi_dung_tong_hop = f"Lịch uống thuốc tổng hợp của bạn ({du_lieu.so_ngay_uong} ngày):\n\n"
                        for thuoc in du_lieu.danh_sach_thuoc:
                            ten_t = thuoc.ten_thuoc or "Thuốc không rõ tên"
                            lieu_l = thuoc.lieu_luong or "Chưa rõ liều lượng"
                            ghi_c = thuoc.ghi_chu or "Không có ghi chú"
                            g_nhac = ', '.join(thuoc.gio_uong_goi_y) if thuoc.gio_uong_goi_y else "Chưa đặt giờ"
                            noi_dung_tong_hop += f"- Thuốc: {ten_t}\n  Liều dùng: {lieu_l}\n  Giờ nhắc: {g_nhac}\n  Ghi chú: {ghi_c}\n\n"
                        
                        gui_email(email_nguoi_dung, "Tổng hợp lịch uống thuốc", noi_dung_tong_hop)
                        cai_dat_hen_gio(du_lieu, email_nguoi_dung)
                        
                        for thuoc in du_lieu.danh_sach_thuoc:
                            with st.expander(thuoc.ten_thuoc or "Thuốc chưa rõ tên"):
                                st.write(f"**Liều dùng:** {thuoc.lieu_luong or 'Chưa rõ liều lượng'}")
                                st.write(f"**Giờ uống báo thức:** {', '.join(thuoc.gio_uong_goi_y) if thuoc.gio_uong_goi_y else 'Chưa đặt giờ'}")
                                if thuoc.ghi_chu: 
                                    st.info(f"**Ghi chú:** {thuoc.ghi_chu}")
                except Exception as e:
                    if "429" in str(e):
                        st.error("Hệ thống AI đang quá tải lượt yêu cầu miễn phí. Vui lòng đợi khoảng 10-15 giây rồi bấm lại nút 'Phân tích'.")
                    else:
                        st.error(f"Lỗi hệ thống: {e}")
