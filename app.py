import streamlit as st
import google.generativeai as genai
import re

# --- 1. 網頁基本設定 ---
st.set_page_config(
    page_title="元朗天主教中學 - 智能選書師", 
    page_icon="📚", 
    layout="wide"
)

# --- 2. 解析多 Key 輪替池（核心安全機制） ---
if "GEMINI_API_KEY" in st.secrets:
    # 自動將用逗號隔開的 Key 轉成清單，並移除前後空格
    api_key_pool = [k.strip() for k in st.secrets["GEMINI_API_KEY"].split(",") if k.strip()]
else:
    api_key_pool = []
    st.error("未能在 Streamlit Secrets 中找到 GEMINI_API_KEY 設定。")

# --- 3. 讀取雙語館藏書單 ---
@st.cache_data
def load_all_books():
    combined_lines = []
    try:
        with open("Chinese_book.txt", "r", encoding="utf-8") as f:
            combined_lines.extend(f.readlines())
    except:
        st.warning("⚠️ 系統提示：未能讀取 Chinese_book.txt")
        
    try:
        with open("English_book.txt", "r", encoding="utf-8") as f:
            combined_lines.extend(f.readlines())
    except:
        st.warning("⚠️ 系統提示：未能讀取 English_book.txt")
        
    return combined_lines

all_book_lines = load_all_books()

# --- 4. 左側專業功能欄 (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/books.png", width=80)
    st.title("YLCS 圖書館")
    st.subheader("📚 智能選書師系統")
    st.markdown("---")
    st.markdown("### 💡 使用小貼士")
    st.caption("同學可以直接輸入你想搵嘅書名、作者或主題（例如：歷史、心理學），亦可以喺下面揀個心情同選書師傾下計，等佢為你調配心靈處方。")
    st.markdown("---")
    st.markdown("### 🌟 心靈充電站")
    st.info("❤️ 人際關係 / 友情 / 溝通\n\n💪 心理勵志 / 情緒舒緩\n\n🎯 考試壓力 / 讀書奮鬥\n\n🌱 孤獨焦慮 / 未來夢想")
    st.markdown("---")
    st.caption("© 元朗天主教中學 圖書館 | 智能AI選書師 v2.7 (穩定測試版)")

# --- 5. 主網頁中央排版 ---
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.title("📚 元朗天主教中學 - 智能選書師")
    st.markdown("### *「每一本書，都是治癒心靈的溫暖配方。」*")
    st.info("👋 **同學仔你好！** 我係你嘅專屬智能選書師。今日過得點呀？無論你想搵特定嘅學術書做 Project，定係想搵本小說散下心、傾下心事，我都會喺我哋學校嘅圖書館館藏度幫你細心挑選最啱你嘅書。👇")

# --- 6. 本地語意關鍵字過濾器 ---
def expand_and_search_books(user_input, book_lines, max_results=20):
    user_input_lower = user_input.lower()
    synonyms_map = {
        "人際關係": ["鬧交", "吵架", "朋友", "同學", "屋企人", "父母", "溝通", "欺凌", "排擠", "拍拖", "分手", "爭執", "不和"],
        "心理勵志": ["唔開心", "傷心", "難過", "頂唔順", "心累", "失敗", "挫折", "正能量", "心靈", "情緒", "哭", "無助", "抑鬱", "難受"],
        "壓力": ["考試", "功課", "測驗", "讀書", "溫書", "sba", "專題", "好累", "壓抑", "溫習", "辛酸", "溫不到", "考不好"],
        "孤獨": ["一個人的", "自閉", "冇人理", "寂寞", "排擠", "孤單", "缺席", "單獨"],
        "焦慮": ["好驚", "緊張", "失眠", "擔心", "未知", "未來", "恐懼", "不知所措", "害怕"],
        "夢想": ["將來", "目標", "迷茫", "前途", "人生", "奮鬥", "堅持", "勇氣", "理想"]
    }
    
    target_tags = []
    for tag, keywords in synonyms_map.items():
        if any(kw in user_input_lower for kw in keywords):
            target_tags.append(tag)
            
    stop_phrases = [
        "我想搵一本", "我想搵幾本", "我想搵本", "有冇關於", "有冇一啲", "你有沒有", "有沒有關於", 
        "我想睇關於", "我想睇一啲", "請幫我搵", "幫我搵下", "有冇介紹", "可唔可以", "請推薦一啲",
        "介紹一啲", "我想知道", "有關於", "我想找", "有沒有", "請幫我", "推薦幾本", "推薦一本",
        "有關", "關於", "我想", "我想要", "搵下", "搵本", "有冇", "搵啲", "睇吓", "睇下", 
        "嘅書", "嘅小說", "嘅藏書", "之類的", "的書", "的小說", "一本書", "幾本書", "有沒有人", "本"
    ]
    
    cleaned_input = user_input
    for phrase in sorted(stop_phrases, key=len, reverse=True):
        cleaned_input = cleaned_input.replace(phrase, " ")
        
    for char in "我你佢想找找有冇嘅的了呢吧嗎請邊度顯示幫推批啲呀啦":
        cleaned_input = cleaned_input.replace(char, " ")
        
    raw_keywords = [k.strip() for k in cleaned_input.split() if len(k.strip()) >= 2]
    target_tags.extend(raw_keywords)
    target_tags = list(set(target_tags))
    
    matched_books = []
    if target_tags:
        for line in book_lines:
            if any(tag in line for tag in target_tags):
                matched_books.append(line.strip())
                
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

# --- 7. 顯示歷史對話 ---
with col2:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 8. 處理同學輸入（Method 2：Streamlit 原生機制在執行時會自動禁用此輸入框，防止重覆提交） ---
    if prompt := st.chat_input("你想搵咩書？或者同我傾下心事..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("選書師正在感同身受，並在館藏中為你挑選心靈配方..."):
                
                relevant_books = expand_and_search_books(prompt, all_book_lines)
                books_context = "\n".join(relevant_books) if relevant_books else "暫時沒有完全匹配的館藏標籤。"
                
                agent_instruction = f"""
                你是「元朗天主教中學 (YLCS) 圖書館智能選書師」。
                
                【目前由系統為同學精選出的相關館藏】：
                {books_context}
                
                【你的核心任務】：
                1. 請先用非常親切、溫暖、充滿校園關懷的廣東話口吻（中學老師的語氣），深入回應學生的心情 or 學術需求。
                2. 從上方提供的【相關館藏】中，挑選出 2 至 3 本最適合、最能幫助同學的書推薦給他們。
                3. **請使用清晰、漂亮、有條理的排版**輸出推薦書籍（嚴禁虛構列表以外的書），格式要求如下：
                   
                   ---
                   ### 📖 推薦書籍：簡短精美呈現
                   - 📚 **書名**：《書名》
                   - 📌 **索書號**：[索書號]
                   - 💡 **心靈推薦原因**：[結合學生的困擾或探究主題，寫出具體且溫暖的推薦理由]
                   - 🔍 **館藏動態查詢**：[👉 點擊這裡查看借閱狀態](https://ylcss.trccloud.hk/opac/search/[處理後的書名])
                   
                   ---
                   
                   ⚠️【網址生成最高指導原則（極重要）】：
                   在填寫上方網址的 `[處理後的書名]` 時，你必須對書名進行以下符號編碼轉換：
                   - **規則 A (空格轉換)**：如果書名內含有「任何空格」（不論前後或中間），你必須將所有的空格全部替換為「+」號。
                     * 例如："Harry Potter" 必須轉換為 `Harry+Potter`
                   - **規則 B (冒號轉換)**：如果書名內含有「半形冒號 :」或「全形冒號 ：」，你必須將所有的冒號全部替換為 `%%3A`（註：在代碼中請輸出為 %%3A 以便正常解析）。
                     * 例如："歷史：中港關係" 必須轉換為 `歷史%%3A中港關係`
                   
                   嚴禁在網址括號 () 內留有任何原始空格或冒號，確保同學點擊時能直接直達學校的 OPAC 系統。
                
                4. 如果【相關館藏】為空，請溫柔地安慰同學，並鼓勵他們換個說法，或隨時親自來圖書館櫃檯搵老師傾計。
                
                同學現在說："{prompt}"
                """
                
                # --- Method 1：核心多 Key 輪替重試機制 ---
                response_text = None
                api_call_success = False
                
                if not api_key_pool:
                    st.error("❌ 系統錯誤：目前沒有可用的 API Key，請檢查 Secrets 設定。")
                else:
                    for idx, current_key in enumerate(api_key_pool):
                        try:
                            # 動態切換當前 Key 並初始化模型
                            genai.configure(api_key=current_key)
                            temp_model = genai.GenerativeModel('gemini-2.5-flash')
                            
                            response = temp_model.generate_content(agent_instruction)
                            response_text = response.text
                            api_call_success = True
                            break  # 成功獲取回覆，立即跳出輪替循環
                        except Exception as e:
                            err_msg = str(e)
                            # 如果遇到 429 流量限制或 Quota 問題，自動跳去下一條 Key
                            if "429" in err_msg or "quota" in err_msg.lower():
                                if idx < len(api_key_pool) - 1:
                                    continue  # 還有後備 Key，繼續下一輪嘗試
                                else:
                                    # 所有 Key 都試過而且都爆了
                                    st.warning("☕ **選書師悄悄話：**\n\n唔好意思啊同學仔！依家圖書館櫃檯真係太熱鬧啦（所有智能通道正忙），選書師需要倒杯水、抖 1 分鐘。請你等陣（大約一分鐘後）再同我傾過啦！如果急嘅話，隨時歡迎你直接行過嚟圖書館櫃檯搵老師傾計㗎！😊")
                            else:
                                # 遇到其他非 429 的程式碼錯誤，直接彈出提示並不進行輪替
                                st.error(f"選書師思考中遇到非流量錯誤。錯誤代碼：{err_msg[:50]}")
                                break
                
                # 如果成功拿到回覆，渲染到網頁並記錄
                if api_call_success and response_text:
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
