import streamlit as st
import google.generativeai as genai
import re

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="元朗天主教中學 - 智能選書師", page_icon="📚", layout="centered")
st.title("📚 元朗天主教中學 - 智能選書師")

# --- 2. 綁定 Google 最新正式版模型 (Gemini 2.5 Flash) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
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

# --- 4. 核心功能：智能語意標籤與口語過濾器 (純本地運行) ---
def expand_and_search_books(user_input, book_lines, max_results=20):
    user_input_lower = user_input.lower()
    
    # 【心靈語意聯想庫】應對同學的情感傾訴
    synonyms_map = {
        "人際關係": ["鬧交", "吵架", "朋友", "同學", "屋企人", "父母", "溝通", "欺凌", "排擠", "拍拖", "分手", "爭執", "不和"],
        "心理勵志": ["唔開心", "傷心", "難過", "頂唔順", "心累", "失敗", "挫折", "正能量", "心靈", "情緒", "哭", "無助", "抑鬱", "難受"],
        "壓力": ["考試", "功課", "測驗", "讀書", "溫書", "sba", "專題", "好累", "壓抑", "溫習", "辛酸", "溫不到", "考不好"],
        "孤獨": ["一個人的", "自閉", "冇人理", "寂寞", "排擠", "孤單", "缺席", "單逐"],
        "焦慮": ["好驚", "緊張", "失眠", "擔心", "未知", "未來", "恐懼", "不知所措", "害怕"],
        "夢想": ["將來", "目標", "迷茫", "前途", "人生", "奮鬥", "堅持", "勇氣", "理想"]
    }
    
    target_tags = []
    
    # 檢查是否命中情感大標籤
    for tag, keywords in synonyms_map.items():
        if any(kw in user_input_lower for kw in keywords):
            target_tags.append(tag)
            
    # 【廣東話尋書口語過濾器】剝離干擾字，精準提取尋書核心主體
    stop_phrases = [
        "我想搵一本", "我想搵幾本", "我想搵本", "有冇關於", "有冇一啲", "你有沒有", "有沒有關於", 
        "我想睇關於", "我想睇一啲", "請幫我搵", "幫我搵下", "有冇介紹", "可唔可以", "請推薦一啲",
        "介紹一啲", "我想知道", "有關於", "我想找", "有沒有", "請幫我", "推薦幾本", "推薦一本",
        "有關", "關於", "我想", "我想要", "搵下", "搵本", "有冇", "搵啲", "睇吓", "睇下", 
        "嘅書", "嘅小說", "嘅藏書", "之類的", "的書", "的小說", "一本書", "幾本書", "有沒有人", "本"
    ]
    
    # 逐步替換掉口語外殼
    cleaned_input = user_input
    for phrase in sorted(stop_phrases, key=len, reverse=True):
        cleaned_input = cleaned_input.replace(phrase, " ")
        
    # 移除單個無實質搜尋意義的常見干擾字
    for char in "我你佢想找找有冇嘅的了呢吧嗎請邊度顯示幫推批啲呀啦":
        cleaned_input = cleaned_input.replace(char, " ")
        
    # 提取長度 >= 2 的核心關鍵字
    raw_keywords = [k.strip() for k in cleaned_input.split() if len(k.strip()) >= 2]
    target_tags.extend(raw_keywords)
    
    # 去除重複關鍵字
    target_tags = list(set(target_tags))
    
    # 在本地進行精準關鍵字撈書
    matched_books = []
    if target_tags:
        for line in book_lines:
            if any(tag in line for tag in target_tags):
                matched_books.append(line.strip())
                
    # 【智能優化兜底機制】如果依然找不到，才進行加權單字匹配
    if not matched_books:
        ignored_chars = "我你佢想找找有冇嘅的了呢吧嗎請邊度顯示幫推本個批啲書版年上下中各與及和或呀啦"
        valid_chars = [c for c in user_input if c not in ignored_chars and not c.isspace()]
        if valid_chars:
            weighted_matches = []
            for line in book_lines:
                match_count = sum(1 for c in valid_chars if c in line)
                if match_count > 0:
                    weighted_matches.append((match_count, line.strip()))
            weighted_matches.sort(key=lambda x: x[0], reverse=True)
            matched_books = [item[1] for item in weighted_matches]
                
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
            
            relevant_books = expand_and_search_books(prompt, all_book_lines)
            books_context = "\n".join(relevant_books) if relevant_books else "暫時沒有完全匹配的館藏標籤。"
            
            # 制定給 Gemini 的溫馨指令
            agent_instruction = f"""
            你是「元朗天主教中學 (YLCS) 圖書館智能選書師」。
            
            【目前由系統為同學精選出的相關館藏】：
            {books_context}
            
            【你的核心任務】：
            1. 請先用非常親切、溫暖、充滿校園關懷的廣東話口吻（中學老師的語氣），深入回應學生的心情或學術需求。
            2. 從上方提供的【相關館藏】中，挑選出 2 至 3 本最適合、最能幫助同學的書推薦給他們。
            3. 必須嚴格按照以下格式輸出推薦書籍（嚴禁虛構列表以外的書）：
               - 書名：《書名》
               - 索書號：[索書號]
               - 💡 心靈推薦原因：[結合學生的困擾或探究主題，寫出具體且溫暖的推薦理由]
               - 🔍 館藏動態查詢：[點擊這裡查看借閱狀態](https://ylcss.trccloud.hk/opac/search/[處理後的書名])
               
               ⚠️【網址生成極重要規則】：
               在填寫上方 [處理後的書名] 時，如果該書名當中「含有任何空格」（常見於英文書名或有副標題的書），你必須將書名入面所有的空格全部替換為「+」號！
               例如：
               - 如果書名是 "Harry Potter"，網址必須輸出為：https://ylcss.trccloud.hk/opac/search/Harry+Potter
               - 如果書名是 "Mental Health 101"，網址必須輸出為：https://ylcss.trccloud.hk/opac/search/Mental+Health+101
               嚴禁在網址括號 () 內留有任何原始空格，否則連結會斷開失效。
            
            4. 如果【相關館藏】為空或裡面確實沒有同學想要的特定主題書籍，請溫柔地安慰同學，並鼓勵他們換個說法，或隨時親自來圖書館櫃檯搵老師傾計。
            
            同學現在說："{prompt}"
            """
            
            try:
                response = model.generate_content(agent_instruction)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"選書師思考中，請稍後再試。錯誤代碼：{str(e)[:50]}")
