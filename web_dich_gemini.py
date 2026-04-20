import streamlit as st
import google.generativeai as genai
import srt
import time
import re

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Gemini 2.5 Global Native - Fix 100%", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    /* Khung nhập liệu và khung kết quả: Nền TRẮNG, Chữ ĐEN */
    .stTextArea textarea { 
        font-family: 'Consolas', monospace; 
        font-size: 16px !important; 
        color: #000000 !important; 
        background-color: #ffffff !important; 
    }
    
    .stButton>button { 
        width: 100%; border-radius: 8px; font-weight: bold; height: 3.5em; 
        background: linear-gradient(45deg, #2979ff, #00e5ff); color: white; border: none; 
    }
    
    .log-box { 
        background-color: #000; color: #00ff41; padding: 15px; border-radius: 8px; 
        height: 300px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

LANGUAGES = [
    "Tiếng Việt", "English", "Japanese", "Korean", "Chinese (Traditional)", 
    "German", "French", "Spanish", "Thai", "Russian", "Portuguese", 
    "Italian", "Indonesian", "Malay", "Arabic", "Dutch", "Turkish", "Hindi"
]

if "logs" not in st.session_state:
    st.session_state.logs = ["--- Hệ thống sẵn sàng (Đã nâng cấp lệnh dịch cưỡng chế) ---"]

def write_log(text):
    st.session_state.logs.append(text)

# --- GIAO DIỆN CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #00e5ff;'>AI GLOBAL TRANSLATOR 2.5 FLASH - CHẾ ĐỘ DỊCH TRIỆT ĐỂ</h2>", unsafe_allow_html=True)

col_k, col_m = st.columns([3, 1])
with col_k:
    api_key = st.text_input("Dán Gemini API Key:", type="password")
with col_m:
    model_id = st.text_input("Model ID:", value="gemini-2.5-flash")

input_text = st.text_area("Nội dung gốc (Dán SRT vào đây):", height=250)

col_l, col_b1, col_up, col_b2 = st.columns([1.5, 1, 1.5, 1])
with col_l:
    target_lang = st.selectbox("Ngôn ngữ đích (Target Language):", LANGUAGES, index=0)
with col_b1:
    btn_translate_text = st.button("✨ Dịch mượt Review")
with col_up:
    uploaded_files = st.file_uploader("Upload file SRT", type=["srt"], accept_multiple_files=True, label_visibility="collapsed")
with col_b2:
    btn_run_files = st.button("🚀 Dịch hàng loạt file")

st.write("Nhật ký thực thi:")
log_placeholder = st.empty()

def refresh_logs():
    log_content = "\n".join(st.session_state.logs)
    log_placeholder.markdown(f'<div class="log-box">{log_content}</div>', unsafe_allow_html=True)

refresh_logs()

# --- PROMPT "CƯỠNG CHẾ" CỰC MẠNH ---
def get_ultimate_native_prompt(content, lang):
    return (
        f"Bạn là một dịch giả chuyên nghiệp xuất sắc nhất thế giới về bản địa hóa phim.\n"
        f"Nhiệm vụ: DỊCH TOÀN BỘ 100% nội dung sau sang {lang}. KHÔNG ĐƯỢC để lại bất kỳ chữ tiếng Trung nào.\n\n"
        f"YÊU CẦU BẮT BUỘC:\n"
        f"1. DỊCH TRIỆT ĐỂ: Thay thế toàn bộ tiếng Trung bằng {lang}. Đối với các tên riêng tiếng Trung, hãy dùng âm Hán Việt (nếu là Tiếng Việt) hoặc phiên âm chuẩn (nếu là ngôn ngữ khác).\n"
        f"2. PHONG CÁCH REVIEW: Dịch ngắn gọn, đúng trọng tâm, phong cách review kể chuyện lôi cuốn. Không dịch dài dòng.\n"
        f"3. GIỮ NGUYÊN MÃ SỐ: Trả về đúng định dạng 'L[X]: nội dung dịch'. Tuyệt đối không thêm lời giải thích.\n"
        f"4. TUYỆT ĐỐI KHÔNG GIỮ NGUYÊN BẢN GỐC.\n\n"
        f"DỮ LIỆU CẦN DỊCH:\n{content}"
    )

# --- HÀM XỬ LÝ CHÍNH ---
def process_srt_strict(model, srt_content, lang):
    try:
        # SỬA LỖI Ở ĐÂY: Dọn dẹp ký tự thừa và BOM tàng hình trước khi phân tích
        srt_content = srt_content.strip()
        if srt_content.startswith('\ufeff'):
            srt_content = srt_content[1:]
            
        subs = list(srt.parse(srt_content))
        batch_size = 10 
        for i in range(0, len(subs), batch_size):
            batch = subs[i : i + batch_size]
            batch_text = "\n".join([f"L{j}: {s.content}" for j, s in enumerate(batch)])
            
            # Gửi yêu cầu dịch
            response = model.generate_content(get_ultimate_native_prompt(batch_text, lang))
            
            if response.text:
                lines = response.text.strip().split('\n')
                for line in lines:
                    match = re.search(r"L(\d+):\s*(.*)", line)
                    if match:
                        try:
                            idx = int(match.group(1))
                            if idx < len(batch):
                                batch[idx].content = match.group(2).strip()
                        except: continue
            
            time.sleep(0.5) # Tránh Rate Limit
        return srt.compose(subs)
    except Exception as e:
        # Trả về lỗi chi tiết để không làm sập cả ứng dụng
        return f"Lỗi xử lý file định dạng SRT: {str(e)}\nHãy chắc chắn file của bạn là chuẩn SRT."

# --- THỰC THI ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)

    if btn_translate_text and input_text:
        write_log(f"⏳ Đang cưỡng chế dịch 100% sang {target_lang}...")
        refresh_logs()
        if "-->" in input_text:
            result = process_srt_strict(model, input_text, target_lang)
            st.text_area("KẾT QUẢ SRT (100% NATIVE):", value=result, height=350)
        else:
            raw_lines = input_text.strip().split('\n')
            formatted = "\n".join([f"L{i}: {line}" for i, line in enumerate(raw_lines)])
            response = model.generate_content(get_ultimate_native_prompt(formatted, target_lang))
            clean_res = re.sub(r"L\d+: ", "", response.text)
            st.text_area("KẾT QUẢ DỊCH:", value=clean_res, height=350)
        write_log("✅ Đã hoàn thành dịch triệt để.")
        refresh_logs()

    if btn_run_files and uploaded_files:
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            write_log(f"📦 Đang xử lý file: {fname}")
            refresh_logs()
            try:
                # SỬA LỖI Ở ĐÂY: Sử dụng utf-8-sig để tự động xóa ký tự BOM gây lỗi crash
                content = uploaded_file.read().decode("utf-8-sig", errors="ignore")
                final_srt = process_srt_strict(model, content, target_lang)
                
                if "Lỗi xử lý file" not in final_srt:
                    st.download_button(label=f"📥 Tải về: {fname}", data=final_srt, file_name=fname.replace(".srt", f"_{target_lang}.srt"), key=fname)
                    write_log(f"✅ Dịch xong file {fname}")
                else:
                    write_log(f"❌ {final_srt}")
                    
                refresh_logs()
            except Exception as e:
                write_log(f"❌ Lỗi đọc file {fname}: {str(e)}")
                refresh_logs()
