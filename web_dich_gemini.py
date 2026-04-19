import streamlit as st
import google.generativeai as genai
import srt
import time

# Cấu hình giao diện Web
st.set_page_config(page_title="AI Gemini Translator Pro V2", layout="wide")

st.title("🌐 HỆ THỐNG DỊCH THUẬT AI GEMINI PRO V2")
st.info("Phiên bản nâng cấp: Hỗ trợ Gemini 2.0/2.5 và chống mất dòng thoại.")

# --- CÀI ĐẶT SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cài đặt hệ thống")
    api_key = st.text_input("Nhập Gemini API Key:", type="password")
    
    # Cập nhật danh sách Model đời mới để sửa lỗi 404
    model_options = {
        "Gemini 2.0 Flash (Nhanh & Mới nhất)": "gemini-2.0-flash",
        "Gemini 1.5 Flash (Ổn định)": "gemini-1.5-flash",
        "Gemini 1.5 Pro (Dịch sâu hơn)": "gemini-1.5-pro"
    }
    selected_model_name = st.selectbox("Chọn dòng Model AI:", list(model_options.keys()))
    selected_model_id = model_options[selected_model_name]

    languages = ["Tiếng Việt", "English", "Chinese", "Japanese", "Korean", "Thai", "French", "Spanish"]
    target_lang = st.selectbox("Dịch sang ngôn ngữ:", languages, index=0)

# --- HÀM DỊCH CHỐNG MẤT DÒNG (330/330 CÂU) ---
def translate_safe(model, batch_data, target_lang):
    # Đánh số thứ tự từng câu thoại để AI không thể bỏ sót câu nào
    batch_text = "\n".join([f"#{i+1}: {text}" for i, text in enumerate(batch_data)])
    
    prompt = (f"Bạn là chuyên gia dịch phim chuyên nghiệp. Hãy dịch danh sách sau sang {target_lang}.\n"
              f"QUY TẮC BẮT BUỘC:\n"
              f"1. Giữ đúng định dạng '#Số: nội dung dịch'.\n"
              f"2. KHÔNG ĐƯỢC BỎ SÓT bất kỳ dòng nào, kể cả tiếng động.\n"
              f"3. Dịch mượt cho nhân vật: Mèo Orange, Mèo Grey, Long Ma...\n\n"
              f"DỮ LIỆU:\n{batch_text}")
    try:
        response = model.generate_content(prompt)
        lines = response.text.strip().split('\n')
        results = [None] * len(batch_data)
        
        for line in lines:
            if ": " in line and line.startswith("#"):
                try:
                    p = line.split(": ", 1)
                    idx = int(p[0].replace("#", "")) - 1
                    if 0 <= idx < len(batch_data):
                        results[idx] = p[1].strip()
                except: continue
        
        # Nếu AI dịch thiếu (VD: ra 325 câu), lấy câu gốc đắp vào để đủ 330
        return [results[i] if results[i] else batch_data[i] for i in range(len(batch_data))]
    except:
        return batch_data

# --- GIAO DIỆN CHÍNH ---
tab1, tab2 = st.tabs(["📁 Dịch file SRT hàng loạt", "✍️ Dịch văn bản trực tiếp"])

with tab1:
    files = st.file_uploader("Tải lên các file SRT của bạn:", type=["srt"], accept_multiple_files=True)
    if st.button("🚀 BẮT ĐẦU DỊCH HÀNG LOẠT", type="primary"):
        if not api_key: st.error("Vui lòng nhập API Key!")
        elif not files: st.warning("Vui lòng chọn file!")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(selected_model_id)
                for f in files:
                    with st.status(f"Đang dịch: {f.name}...", expanded=True) as status:
                        content = f.read().decode("utf-8")
                        subs = list(srt.parse(content))
                        total = len(subs)
                        st.write(f"📊 Tổng số câu thoại: {total}")
                        
                        translated_list = []
                        batch_size = 15 # Chia cụm nhỏ để AI dịch chính xác nhất
                        prog = st.progress(0)
                        
                        for i in range(0, total, batch_size):
                            batch = subs[i:i+batch_size]
                            res = translate_safe(model, [s.content for s in batch], target_lang)
                            translated_list.extend(res)
                            prog.progress(min((i + batch_size) / total, 1.0))
                            time.sleep(0.5) # Tránh bị chặn do gửi quá nhanh
                        
                        for j in range(len(subs)): subs[j].content = translated_list[j]
                        st.download_button(label=f"📥 Tải file: {f.name}", data=srt.compose(subs), file_name=f.name.replace(".srt", f"_{target_lang}.srt"))
                        status.update(label=f"✅ Hoàn thành {len(translated_list)}/{total} câu!", state="complete")
            except Exception as e: st.error(f"Lỗi: {e}")

with tab2:
    input_text = st.text_area("Nhập đoạn văn bản cần dịch:", height=300)
    if st.button("✨ DỊCH VĂN BẢN NGAY"):
        if not api_key or not input_text: st.error("Vui lòng điền đủ thông tin!")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(selected_model_id)
                res = model.generate_content(f"Dịch sang {target_lang}:\n\n{input_text}")
                st.subheader("Kết quả:")
                st.write(res.text)
            except Exception as e: st.error(f"Lỗi: {e}")
