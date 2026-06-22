import streamlit as st
import google.generativeai as genai
import re
import random  # 引入隨機庫，用於激活盲盒洗牌機制
import json    # 用於解析 Secrets 中的 JSON 字串
from datetime import datetime, timedelta # 用於生成精準的香港時間戳記
import gspread # 引入 Google Sheets 官方對接庫
from google.oauth2.service_account import Credentials

# --- 1. 網頁基本設定 ---
st.set_page_config(
    page_title="元天閱讀腦朋友 - YLCSS 圖書館", 
    page_icon="📚", 
    layout="wide"  # 使用寬版頁面
)

# --- 2. 解析多 Key 輪替池（核心安全機制：應對 429 流量限制） ---
if "GEMINI_API_KEY" in st.secrets:
    # 自動將 Secrets 中用英文逗號隔開的 Key 轉成清單，並移除前後空格
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

# --- 💡 默默寫入 Google Sheet 原始數據頁的背景函數 ---
def log_search_intent_to_sheets(prompt, tags_str, keywords_str):
    try:
        # 1. 安全讀取 Secrets 裡面的憑證與網址
        if "GCP_JSON_STR" not in st.secrets or "GOOGLE_SHEET_URL" not in st.secrets:
            return # 若未設定，靜默退出，不干擾學生使用
            
        creds_dict = json.loads(st.secrets["GCP_JSON_STR"])
        sheet_url = st.secrets["GOOGLE_SHEET_URL"]
        
        # 2. 設定權限範圍並授權
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 3. 打開指定試算表並鎖定 Raw_Data 工作表
        sh = client.open_by_url(sheet_url)
        worksheet = sh.worksheet("Raw_Data")
        
        # 4. 生成香港時間 (UTC+8)
        hkt_now = datetime.utcnow() + timedelta(hours=8)
        timestamp = hkt_now.strftime("%Y-%m-%d %H:%M")
        
        # 5. 打包成新的一行數據 [時間, 原句, 標籤, 關鍵字]
        row_data = [timestamp, prompt, tags_str, keywords_str]
        
        # 6. 默默寫入 Google Sheet
        worksheet.append_row(row_data)
    except Exception as e:
        # 僅在後台打印錯誤，絕對不彈出 error 破壞學生的聊天介面
        print(f"Google Sheets Logging Error: {e}")

# --- 4. 左側專業功能欄 (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/books.png", width=80)
    st.title("YLCSS 圖書館")
    st.subheader("📚 元天閱讀腦朋友")
    st.markdown("---")
    st.markdown("### 💡 使用小貼士")
    st.caption("同學可以直接輸入你想搵嘅書名、作者或主題（例如：歷史、心理學），亦可以喺下面揀個心情同腦朋友傾下計，等佢為你調配心靈處方。")
    st.markdown("---")
    st.markdown("### 🌟 心靈充電站")
    st.info("❤️ **阿樂 / 阿細 / 阿厭**\n人際關係 | 自我接納 | 慢活日常\n\n💪 **阿愁 / 阿焦**\n心理勵志 | 療癒減壓 | 讀書應試\n\n🎯 **阿燥 / 阿驚**\n正義對抗 | 熱血競技 | 危機求生")
    st.markdown("---")
    st.caption("© 元朗天主教中學 圖書館 |\n元天閱讀腦朋友 v3.2 (數據優化版)")

# --- 5. 主網頁標頭（全螢幕標準寬度，確保內容清晰） ---
st.title("📚 元天閱讀腦朋友")
st.markdown("### *「每一本書，都是治癒心靈的溫慢配方。」*")
st.info("👋 **同學仔你好！** 我係你嘅專屬「元天閱讀腦朋友」。今日過得點呀？無論你想搵特定嘅學術書做 Project，定係想搵本小說散下心、傾下心事，我幕後都會喺我哋學校嘅圖書館館藏度幫你細心挑選最啱你嘅書。👇")

# --- 6. 本地語意關鍵字過濾器（全面升級版：融入100+大數據圖書標籤與廣東話對接） ---
def expand_and_search_books(user_input, book_lines, max_results=20):
    user_input_lower = user_input.lower()
    
    # 核心映射字典：將同學可能輸入的口語、情境，精準對接去 KB 的專業標籤
    synonyms_map = {
        # === 1. 情感、心靈與成長 ===
        "成長": ["成長", "長大", "成熟", "大個仔", "大個女", "蛻變", "獨立", "生存"],
        "勇氣": ["勇氣", "勇氣", "大膽", "唔驚", "勇敢", "不畏", "直面"],
        "堅持": ["堅持", "努力", "不放棄", "拼搏", "奮鬥", "堅韌", "生命韌性"],
        "自信": ["自信", "信心", "信自己", "有把握"],
        "突破": ["突破", "超越", "更進一步"],
        "自我探索": ["自我探索", "自我接納", "內在", "認同", "自己是誰"],
        "智慧": ["智慧", "思考", "啟發", "啟蒙", "哲學", "心靈"],
        "快樂": ["快樂", "開心", "歡樂", "歡笑", "笑聲", "熱情", "樂觀", "滿足", "感恩"],
        "信仰": ["信仰", "虔誠", "道德"],
        "選擇": ["選擇", "抉擇", "價值", "方向"],
        "友誼": ["友誼", "友情", "真摯", "夥伴", "陪伴", "朋友", "同學", "死黨", "班房", "同窗"],
        "分享": ["分享", "溫柔", "關愛", "同理", "同理心", "信任", "合作", "團隊", "協作", "團結"],
        "親情": ["親情", "家庭", "親子", "手足", "爸爸", "媽媽", "父母", "屋企人", "傳承", "回憶"],
        "愛": ["愛", "真愛", "愛情", "拍拖", "結婚", "出pool", "戀愛"],
        "歸屬": ["歸屬", "歸屬感", "接納", "包容"],
        "驚喜": ["驚喜", "特別", "禮物", "儀式感"],
        "孤獨": ["孤獨", "孤單", "寂寞", "一個人的", "自閉", "冇人理", "邊緣"],
        "恐懼": ["恐懼", "好驚", "驚驚", "害怕", "緊張", "不知所措", "安全感", "惡夢"],
        "挫折": ["挫折", "失敗", "頂唔順", "心累", "難過", "傷心", "唔開心", "痛苦", "失去", "苦難"],
        "求生": ["求生", "逃脫", "危機", "生存本能", "保護"],
        "霸凌": ["霸凌", "欺凌", "排擠", "笑我", "話我"],
        "療癒": ["療癒", "舒緩", "放鬆", "安慰", "哭"],
        "叛逆": ["叛逆", "反叛", "唔聽話", "衝突", "誘惑"],

        # === 2. 冒險、奇幻與時空歷史 ===
        "魔法": ["魔法", "奇幻", "奇幻冒險", "夢幻", "夢想", "童話", "寓言", "神話", "傳說", "魔咒", "巫術", "精靈", "阿拉丁"],
        "神秘": ["神秘", "謎團", "日記", "哥特美學", "外星"],
        "正義": ["正義", "英雄", "使命", "反抗", "反擊", "對抗", "復仇", "責任", "指引"],
        "搞笑": ["搞笑", "惡搞", "惡作劇", "瘋狂", "荒謬", "荒誕", "荒誕幽默", "黑色幽默", "間諜", "機智", "解悶"],
        "歷史": ["歷史", "歷史現場", "古文明", "文明", "帝國興衰", "榮耀", "王權", "權力", "革命", "戰爭", "戰爭記憶", "記憶", "光明", "希望"],
        "戰士": ["戰士", "武器", "騎士", "城堡", "武士"],
        "偉人": ["偉人", "傳記", "領袖", "領導"],

        # === 3. 科學、技術與自然生態 ===
        "科學": ["科學", "趣味科學", "技術", "科技", "創新", "發明", "創意", "創造力", "腦力", "結構", "支撐", "隱形力量", "氣體", "微觀宇宙", "生命密碼", "宇宙", "時間", "循環", "數字", "機械", "築夢"],
        "自然": ["自然", "自然史詩", "生態", "敬畏", "環境", "環保", "未來", "地球", "污染", "行動", "美好", "遼闊"],
        "海洋": ["海洋", "世界", "地理", "天氣", "風暴", "災難", "海洋記憶", "漂流瓶", "命運交會"],
        "極地": ["極地", "極地生活", "沙漠", "荒野", "森林", "冰雪", "河流"],
        "演化": ["演化", "生命樹", "根源", "瀕危", "保育", "季節", "適應", "適應力"],
        "動物": ["動物", "動物日常", "野生", "昆蟲", "大象", "貓咪", "熊", "魚類", "奇觀", "爬蟲", "幼崽", "可愛", "溫馨", "寵物", "洗澡", "觀察", "攝影", "澳洲", "澳洲風情", "植物", "晨光"],

        # === 4. 社會、城市與日常百態 ===
        "文化": ["文化", "文化差異", "文化熔爐", "傳統", "認同", "根脈", "節慶", "文化交融", "傳統文化", "美國夢", "亞洲", "反思"],
        "美食": ["美食", "饗宴", "飲食", "飲食文化", "民間", "聖誕"],
        "生活": ["生活", "日常", "日常驚喜", "工作", "市集", "居住", "居住智慧", "多樣性", "人文", "社區", "家", "家園", "城市", "倫敦", "埃及", "旅行", "購物", "午餐", "金錢", "金融", "制度"],

        # === 5. 學習、體藝與視聽傳播 ===
        "學習": ["學習", "趣味", "基礎", "知識", "遊戲", "互動", "字母", "模仿", "塗鴉", "語法", "邏輯", "表達", "表達藝術", "文字", "力量", "校對", "精確", "專業", "創作", "練習"],
        "應試": ["應試", "考試", "技巧", "測驗", "exam", "quiz", "test", "sba", "dse", "溫書", "讀書"],
        "聆聽練習": ["聆聽練習", "語言節奏", "跨文化", "專注力", "聲音解碼", "溝通藝術", "語感培養", "情境理解", "聲音地圖", "深度聆聽", "情感共鳴", "聲音詩篇", "溝通", "對話"],
        "音樂": ["音樂", "舞蹈", "芭蕾", "優雅", "節奏", "舞台"],
        "運動": ["運動", "棒球", "熱血", "傳奇", "紀錄", "球員", "勵志", "滑輪", "跌倒", "速度", "自由"],
        "校園": ["校園", "火車", "汽車", "單車", "頭髮", "假髮", "童年", "童真"],
        "電影": ["電影", "幕後", "時尚", "網絡", "時代", "網絡時代", "連結", "影響", "動畫"]
    }
    
    target_tags = []
    triggered_emotions = [] # 用於單獨紀錄觸發了哪些心理與學術標籤
    
    for tag, keywords in synonyms_map.items():
        if any(kw in user_input_lower for kw in keywords):
            target_tags.append(tag)
            triggered_emotions.append(tag)
            
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
                
        # 盲盒機制：打亂精確匹配到的書單
        random.shuffle(matched_books)
                
    if not matched_books:
        # 模糊權重匹配
        ignored_chars = "我你佢想找找有冇嘅的了呢吧嗎請邊度顯示幫推本個批啲書版年上下中各與及和或呀啦"
        valid_chars = [c for c in user_input if c not in ignored_chars and not c.isspace()]
        if valid_chars:
            weighted_matches = []
            for line in book_lines:
                match_count = sum(1 for c in valid_chars if c in line)
                if match_count > 0:
                    weighted_matches.append((match_count, line.strip()))
            
            # 打亂相同權重分數的書
            random.shuffle(weighted_matches)
            weighted_matches.sort(key=lambda x: x[0], reverse=True)
            matched_books = [item[1] for item in weighted_matches]
                
    # 將標籤清單、關鍵字清單用英文逗號組合成字串，方便後台儲存統計
    tags_str = ",".join(triggered_emotions) if triggered_emotions else ""
    keywords_str = ",".join(raw_keywords) if raw_keywords else ""
    
    return matched_books[:max_results], tags_str, keywords_str

# --- 7. 顯示歷史對話（直屬根目錄以支援完美捲動） ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 8. 處理同學輸入（Streamlit 自動永久固定喺網頁最底部） ---
if prompt := st.chat_input("你想搵咩書？或者同我傾下心事..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("「元天閱讀腦朋友」正在聽你傾訴，並在館藏中為你挑選心靈配方..."):
            
            # 1. 調用優化後的搜尋過濾器，順便獲取標籤與關鍵字字串
            relevant_books, triggered_tags_str, keywords_str = expand_and_search_books(prompt, all_book_lines)
            books_context = "\n".join(relevant_books) if relevant_books else "暫時沒有完全匹配的館藏標籤。"
            
            # 2. 默默將不記名搜尋意圖側錄上傳至 Google Sheet
            log_search_intent_to_sheets(prompt, triggered_tags_str, keywords_str)
            
            # 3. 構築 AI 指令 (完美對接「腦朋友」8大情緒角色模型)
            agent_instruction = f"""
            你是「元朗天主教中學 (YLCSS) 圖書館」專屬的 AI 夥伴——「元天閱讀腦朋友」。
            
            【目前由系統為同學精選出的相關館藏】：
            {books_context}
            
            【你的腦朋友情緒分類核心邏輯】：
            你可以靈活運用《玩轉腦朋友 2》的 8 個情緒角色口吻為同學開導，並根據書籍所帶的標籤進行專業的心靈處方配對：
            1. 阿樂 (Joy) - 適合標籤：成長、勇氣、自信、快樂、熱情、樂觀、友誼、分享、愛、夢想、音樂、運動、童年。
            2. 阿愁 (Sadness) - 適合標籤：孤獨、失去、苦難、療癒、回憶、親情、同理心、哲學。
            3. 阿燥 (Anger) - 適合標籤：反抗、衝突、復仇、霸凌、戰爭、正義。
            4. 阿驚 (Fear) - 適合標籤：恐懼、黑暗、惡夢、求生、保護、神秘、災難。
            5. 阿憎 (Disgust) - 適合標籤：叛逆、惡搞、荒謬、黑色幽默、搞笑、時尚、文化差異。
            6. 阿焦 (Anxiety) - 適合標籤：應試、壓力、精確、未來、責任、金錢。
            7. 阿細 (Envy) - 適合標籤：自我探索、突破、文化融合、渴望。
            8. 阿厭 (Ennui) - 適合標籤：日常、生活、自然、動物、網絡、電影、旅行、慢活。
            
            【你的核心任務】：
            1. 請先用非常親切、溫慢、充滿校園關懷的廣東話口吻（中學老師與知心好友的雙重語氣），深入回應學生的心情 or 學術需求。可以適當提及是哪位「腦朋友」正在為他們調配這個處方。
            2. 從上方提供的【相關館藏】中，挑選出 3 至 4 本最適合、最能幫助同學的書推薦給他們。
            3. **請使用清晰、漂亮、有條理的排版**輸出推薦書籍（嚴禁虛構列表以外的書），格式要求如下：
               
               ---
               ### 📖 推薦書籍
               - 📚 **書名**：《書名》
               - 📌 **索書號**：[索書號]
               - 💡 **心靈推薦原因**：[結合學生的困擾或探究主題，寫出具體且溫暖的推薦理由，並點出這本書對應的腦朋友特質]
               - 🔍 **館藏動態查詢**：[👉 點擊這裡查看借閱狀態](https://ylcss.trccloud.hk/opac/search/[處理後的書名])
               
               ---
               
               ⚠️【網址生成最高指導原則（極重要）】：
               在填寫上方網址的 `[處理後的書名]` 時，你必須對書名進行以下符號編碼轉換：
               - **規則 A (空格轉換)**：如果書名內含有「任何空格」（不論前後或中間），你必須將所有的空格全部替換為「+」號。
                 * 例如："Harry Potter" 必須轉換為 `Harry+Potter`
               - **規則 B (冒號轉換)**：如果書名內含有「半形冒號 :」或「全形冒號 ：」，你必須將所有的冒號全部替換為 `%%3A`（註：在代碼中請輸出為 %%3A 以便正常解析）。
                 * 例如("歷史：中港關係" 必須轉換為 `歷史%%3A中港關係`)
               
               嚴禁在網址括號 () 內留有任何原始空格 or 冒號，確保同學點擊時能直接直達學校的 OPAC 系統。
            
            4. 如果【相關館藏】為空，請溫柔地安慰同學，並鼓勵他們換個說法，或隨時親自來圖書館櫃檯搵老師、搵「腦朋友」本尊傾計。
            
            同學現在說："{prompt}"
            """
            
            # --- 多 Key 輪替重試機制 ---
            response_text = None
            api_call_success = False
            
            if not api_key_pool:
                st.error("❌ 系統錯誤：目前沒有可用的 API Key，請檢查 Secrets 設定。")
            else:
                for idx, current_key in enumerate(api_key_pool):
                    try:
                        genai.configure(api_key=current_key)
                        temp_model = genai.GenerativeModel('gemini-2.5-flash')
                        
                        response = temp_model.generate_content(agent_instruction)
                        response_text = response.text
                        api_call_success = True
                        break
                    except Exception as e:
                        err_msg = str(e)
                        if "429" in err_msg or "quota" in err_msg.lower():
                            if idx < len(api_key_pool) - 1:
                                continue
                            else:
                                st.warning("☕ **閱讀腦朋友悄悄話：**\n\n唔好意思啊同學仔！依家圖書館櫃檯真係太熱鬧啦（所有智能通道正忙），腦朋友需要倒杯水、抖 1 分鐘。請你等陣（大約一分鐘後）再同我傾過啦！如果急嘅話，隨時歡迎你直接行過嚟圖書館櫃檯搵老師傾計㗎！😊")
                        else:
                            st.error(f"腦朋友思考中遇到非流量錯誤。錯誤代碼：{err_msg[:50]}")
                            break
            
            if api_call_success and response_text:
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
