import streamlit as st
import google.generativeai as genai

# --- UI 介面設定 ---
st.set_page_config(page_title="元朗天主教中學 - 智能選書師", page_icon="📚", layout="centered")
st.title("📚 元朗天主教中學 - 智能選書師")

# --- 設定 API Key ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 讀取書單 ---
@st.cache_data
def load_books():
    try:
        with open("books.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "書單載入失敗"

book_list = load_books()

# --- 核心邏輯：自動偵測可用模型 ---
def get_model():
    # 嘗試抓取所有可用的模型列表
    models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
    
    # 優先選擇 flash 模型，如果搵唔到就攞第一個可用嘅
    target_model = "gemini-1.5-flash"
    if target_model not in models:
        # 如果搵唔到指定模型，直接用系統列表入面第一個 gemini 開頭嘅模型
        target_models = [m for m in models if "gemini" in m]
        target_model = target_models[0] if target_models else models[0]
    
    return genai.GenerativeModel(model_name=target_model)

# --- 處理對話 ---
try:
    model = get_model()
    # (其餘對話邏輯不變...)
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("輸入你想搵嘅書..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            chat = model.start_chat(history=[])
            response = chat.send_message(f"書單資料: {book_list}\n\n用戶要求: {prompt}")
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

except Exception as e:
    st.error(f"系統自動抓取模型失敗，請確認 API Key 是否有效。錯誤細節：{str(e)}")
