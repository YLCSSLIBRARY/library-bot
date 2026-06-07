import streamlit as st
import google.generativeai as genai
import re

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="元朗天主教中學 - 智能選書師", page_icon="📚", layout="centered")
st.title("📚 元朗天主教中學 - 智能選書師")

# --- 2. 綁定 Google 最新免費模型 ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("API Key 設定有誤，請聯絡管理員檢查 Streamlit Secrets。")

# --- 3. 讀取館藏與心靈標籤庫 ---
@st.cache_data
def load_all_books():
    try:
        with open("books.txt", "r", encoding="utf-8") as f:
            return f.readlines()
    except:
        return []

all_book_lines = load_all_books()

# --- 4. Python 本地標籤極速檢索演算法 (Agent Tools) ---
def search_local_books(user_prompt, book_lines, max_results=15):
    # 拆解學生的輸入，過濾掉無意義字詞，提取核心關鍵字/情感詞
    ignore_chars = "我你他她想找有咩關於的了呢吧嗎啊好近排唔該請介紹睇"
    search_terms = [word for word in re.split(r'[ ,.?!，。？！、]', user_prompt) if word]
    
    # 如果整句打埋一齊，就進行字元過濾
    if len(search_terms) == 1:
        search_terms = [c for c in user_prompt if c not in ignore_chars]
        
    matched_books = []
    # 優先完全匹配關鍵字/標籤
    for line in book_lines:
        if any(term in line for term in search_terms if len(term) > 0):
            matched_books.append(line.strip())
            
    # 如果搵到太多，精選前 max_results 本；如果太少，就隨機比一些或者保留全部
    return matched_books[:max_results]

# --- 5. 對話歷史介面 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 處理同學輸入與心靈推薦 ---
if prompt := st.chat_input("你想搵咩書？或者同我傾下心事..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # A. 透過 Python 先行利用老師的「心靈標籤」進行精準篩選
        relevant_books = search_local_books(prompt, all_book_lines)
        
        # B. 將篩選後的結果組裝成給 Gemini 的上下文
        books_context = "\n".join(relevant_books) if relevant_books else "暫時沒有完全匹配的館藏標籤。"
        
        # C. 制定嚴格的 AI 推薦指令
        agent_instruction = f"""
        你是「元朗天主教中學 (YLCS) 圖書館智能選書師」。
        
        【目前圖書館經過標籤篩選後的相關館藏如下】：
        {books_context}
        
        【你的任務】：
        1. 請先用非常親切、溫暖、具校園關懷的廣東話口吻，回應學生的心情或學術需求（例如：安慰他們的考試壓力，或鼓勵他們的專題研習）。
        2. 從上方提供的【相關館藏】中，精心挑選出 2 至 3 本最適合學生的書推薦給他們。
        3. 必須嚴格按照以下格式輸出推薦書籍（嚴禁虛構此列表以外的書）：
           - 書名：《書名》
           - 索書號：[索書號]
           - 💡 心靈推薦原因：[結合學生的需求與你在館藏中看到的標籤，寫出溫暖的推薦理由]
           - 🔍 館藏動態查詢：[點擊這裡查看借閱狀態](https://ylcss.trccloud.hk/opac/search/[書名])
        
        4. 如果【相關館藏】為空，請溫柔地告訴同學目前可能沒有完全脗合心靈標籤的書，但鼓勵他們直接輸入其他關鍵字，或親自來圖書館櫃檯搵老師傾計，老師會為他們手動選書。
        
        同學現在說："{prompt}"
        """
        
        try:
            # 呼叫 AI 進行精準、具備靈魂的心靈對話
            response = model.generate_content(agent_instruction)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"選書師思考中，請稍後再試。錯誤代碼：{str(e)[:50]}")
