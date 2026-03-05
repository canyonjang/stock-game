import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. 기본 설정 및 연결 ---
st.set_page_config(page_title="주식 매매 게임", page_icon="📈", layout="centered")

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def init_connection():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

client = init_connection()
doc = client.open("주식 매매 게임")

ws_status = doc.worksheet("상태")
ws_assets = doc.worksheet("학생자산")
ws_orders = doc.worksheet("주문장")

# --- 2. 🛡️ 40명 동시 접속 방어 (TTL 캐싱) ---
# 구글 시트에서 데이터를 읽어오는 작업을 2초마다 한 번만 수행하도록 제한합니다.
@st.cache_data(ttl=2)
def get_market_data():
    s_data = ws_status.get_all_records()
    a_data = ws_assets.get_all_records()
    return s_data, a_data

# 캐싱된 함수를 호출하여 데이터를 가져옵니다.
status_data, assets_data = get_market_data()

current_round = status_data[0]['현재라운드']
fair_value = status_data[0]['주식적정가치']
df_assets = pd.DataFrame(assets_data)

# --- 3. 학생용 화면 구성 ---
st.title("📈 주식 매매 게임")
st.info(f"**현재 라운드:** {current_round} 라운드 (수학적 적정 가치: {fair_value}달러)")

st.write("---")

student_id_input = st.text_input("자신의 학번을 입력하세요 (예: 10101)", "")

if student_id_input:
    try:
        student_id = int(student_id_input)
        student_info = df_assets[df_assets['학번'] == student_id]
        
        if not student_info.empty:
            student_name = student_info.iloc[0]['이름']
            cash = student_info.iloc[0]['보유현금']
            shares = student_info.iloc[0]['보유주식수']
            
            st.success(f"환영합니다, **{student_name}** 펀드매니저님!")
            
            col1, col2 = st.columns(2)
            col1.metric("보유 현금", f"${cash}")
            col2.metric("보유 주식", f"{shares}주")
            
            st.write("---")
            st.subheader("📝 주문 입력기")
            
            with st.form("order_form"):
                order_type = st.radio("주문 종류", ["매수 (살래)", "매도 (팔래)"], horizontal=True)
                price = st.number_input("희망 가격 (달러)", min_value=1, max_value=50, step=1)
                quantity = st.number_input("수량 (주)", min_value=1, max_value=50, step=1)
                
                submitted = st.form_submit_button("주문 전송")
                
                if submitted:
                    if order_type == "매수 (살래)" and (price * quantity) > cash:
                        st.error(f"보유 현금이 부족합니다! (필요 현금: ${price * quantity})")
                    elif order_type == "매도 (팔래)" and quantity > shares:
                        st.error(f"보유 주식이 부족합니다! (현재 보유: {shares}주)")
                    else:
                        clean_type = "매수" if "매수" in order_type else "매도"
                        new_row = [current_round, student_id, clean_type, price, quantity]
                        ws_orders.append_row(new_row)
                        
                        st.success(f"✅ {clean_type} 주문 접수 완료! (가격: ${price}, 수량: {quantity}주)")
                        
        else:
            st.warning("등록되지 않은 학번입니다. 오타가 없는지 확인해주세요.")
            
    except ValueError:
        st.error("학번은 숫자만 입력해주세요.")
