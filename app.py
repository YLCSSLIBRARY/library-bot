import streamlit as st
import google.generativeai as genai
import re

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="元朗天主教中學 - 智能選書師", page_icon="📚", layout="centered")
st.title("📚 元朗天主教中學 - 智能選書師")

# --- 2. 綁定 Google 真正穩定免費的模型 (Gemini 1.5 Flash) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 使用官方最穩定、對香港免 VPN 開放的免費主力模型
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("API Key 設定有誤，請檢查 Streamlit Secrets 設定。")

# --- 3. 讀取館藏書單 ---
@st.cache_data
def load_all_books():
    try:
        with open("books.txt", "r", encoding="utf-8") as f:
            return f.readlines()
    except:
        return []

all_book_lines = load_all_books()

# --- 4. 核心功能：智能語意標籤擴展器 (純本地運行，0延時，不佔用API配額) ---
def expand_and_search_books(user_input, book_lines, max_results=20):
    user_input_lower = user_input.lower()
    
    # 【心靈語意聯想庫】將學生的口語，完美對接老師你辛苦建立的心靈標籤
    synonyms_map = {
        "人際關係": ["鬧交", "吵架", "朋友", "同學", "屋企人", "父母", "溝通", "欺凌", "排擠", "拍拖", "分手", "爭執"],
        "心理勵志": ["唔開心", "傷心", "難過", "頂唔順", "心累", "失敗", "挫折", "正能量", "心靈", "情緒", "哭", "無助"],
        "壓力": ["考試", "功課", "測驗", "讀書", "溫書", "sba", "專題", "好累", "壓抑", "頂唔順", "溫習", "辛酸"],
        "孤獨": ["一個人的", "自閉", "冇人理", "寂寞", "排擠", "孤單", "缺席"],
        "焦慮": ["好驚", "緊張", "失眠", "擔心", "未知", "未來", "恐懼", "不知所措"],
        "夢想": ["將來", "目標", "迷茫", "前途", "人生", "奮鬥", "堅持", "勇氣", "理想"],
        "歷史": ["歷史", "中國", "古代", "朝代", "故事", "三國", "世界大戰", "過去"]
    }
    
    target_tags = []
    
    # 1. 語意聯想：如果學生對話中包含相關情感口語，自動加入對應的心靈大標籤
    for tag, keywords in synonyms_map.items():
        if any(kw in user_input_lower for kw in keywords):
            target_tags.append(tag)
    
    # 2. 提取原本輸入的關鍵字（過濾掉太短的單字）
    raw_words = [w for w in re.split(r'[ ,.?!，。？！、]', user_input) if len(w) > 1]
    target_tags.extend(raw_words)
    
    # 去除重複字詞
    target_tags = list(set(target_tags))
    
    # 3. 在本地書單進行智能撈書
    matched_books = []
    if target_tags:
        for line in book_lines:
            if any(tag in line for tag in target_tags):
                matched_books.append(line.strip())
                
    # 安全機制：如果用聯想庫找不到，就用最基礎的單字模糊匹配，確保一定有書，不讓畫面空白
    if not matched_books:
        for line in book_lines:
            if any(char in line for char in user_input if char not in "我你他想找的有咩關於的了呢吧嗎請"):
                matched_books.append(line.strip())
                
    return matched_books[:max_results]

# --- 5. 對話歷史介面 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 處理同學輸入與心靈關懷推薦 ---
if prompt := st.chat_input("你想搵咩書？或者同我傾下心事..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("選書師正在感同身受，並在館藏中為你挑選心靈配方..."):
            
            # 本地秒速完成語意聯想，撈出 20 本相關書目
            relevant_books = expand_and_search_books(prompt, all_book_lines)
            books_context = "\n".join(relevant_books) if relevant_books else "暫時沒有完全匹配的館藏標籤。"
            
            # 制定給 Gemini 的溫暖指令（只餵給他 20 本精選書，Token 極小，永不爆量）
            agent_instruction = f"""
            你是「元朗天主教中學 (YLCS) 圖書館智能選書師」。
            
            【目前由系統根據你的心靈標籤，為同學精選出的相關館藏】：
            {books_context}
            
            【你的核心任務】：
            1. 請先用非常親切、溫暖、充滿校園關懷的廣東話口吻（中學老師的語氣），深入回應學生的心情或學術需求（例如安慰他們的考試壓力、人際關係鬧交的難過，或引導專題研習）。
            2. 從上方提供的【相關館藏】中，挑選出 2 至 3 本最適合、最能幫助同學的書推薦給他們。
            3. 必須嚴格按照以下格式輸出推薦書籍（嚴禁虛構列表以外的書）：
               - 書名：《書名》
               - 索書號：[索書號]
               - 💡 心靈推薦原因：[結合學生的困擾與這本書的標籤，寫出具體且溫暖的推薦理由]
               - 🔍 館藏動態查詢：[點擊這裡查看借閱狀態](https://ylcss.trccloud.hk/opac/search/[書名])
            
            4. 如果【相關館藏】為空或不夠匹配，請溫柔地安慰同學，並鼓勵他們換個說法，或隨時親自來圖書館櫃檯搵老師傾計，老師會為他們手動選書。
            
            同學現在說："{prompt}"
            """
            
            try:
                # 呼叫真正穩定的官方免費 Gemini 1.5 Flash
                response = model.generate_content(agent_instruction)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"選書師思考中，請稍後再試。錯誤代碼：{str(e)[:50]}")
