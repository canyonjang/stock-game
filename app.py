import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. 기본 설정 및 연결 ---
# (st.set_page_config 부분은 기존과 동일하게 두세요)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# @st.cache_resource를 활용해 구글 시트 탭 3개를 한 번만 불러와서 기억(캐싱)해 둡니다.
@st.cache_resource
def init_connection():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    doc = client.open("주식 매매 게임")
    
    # 시트 3개를 여기서 미리 다 찾아서 반환합니다.
    return (
        doc.worksheet("상태"),
        doc.worksheet("학생자산"),
        doc.worksheet("주문장")
    )

# 캐싱된 함수를 실행해 3개의 시트 변수를 받아옵니다.
ws_status, ws_assets, ws_orders = init_connection()

# --- 2. 데이터 불러오기 ---
# 현재 게임 상태 데이터 가져오기
status_data = ws_status.get_all_records()
current_round = status_data[0]['현재라운드']
fair_value = status_data[0]['주식적정가치']

# 학생 자산 데이터 가져오기 (데이터프레임 변환)
assets_data = ws_assets.get_all_records()
df_assets = pd.DataFrame(assets_data)

# --- 3. 학생용 화면 구성 ---
st.title("📈 주식 매매 게임")
st.info(f"**현재 라운드:** {current_round} 라운드 (수학적 적정 가치: {fair_value}달러)")

st.write("---")

# 학번 입력란
student_id_input = st.text_input("자신의 학번을 입력하세요 (예: 10101)", "")

# 학번이 입력되었을 때만 아래 화면 보여주기
if student_id_input:
    try:
        student_id = int(student_id_input)
        # 입력한 학번과 일치하는 학생 정보 찾기
        student_info = df_assets[df_assets['학번'] == student_id]
        
        if not student_info.empty:
            student_name = student_info.iloc[0]['이름']
            cash = student_info.iloc[0]['보유현금']
            shares = student_info.iloc[0]['보유주식수']
            
            st.success(f"환영합니다, **{student_name}** 펀드매니저님!")
            
            # 현재 자산 깔끔하게 보여주기
            col1, col2 = st.columns(2)
            col1.metric("보유 현금", f"${cash}")
            col2.metric("보유 주식", f"{shares}주")
            
            st.write("---")
            st.subheader("📝 주문 입력기")
            
            # --- 4. 주문 폼 (Form) ---
            with st.form("order_form"):
                order_type = st.radio("주문 종류", ["매수 (살래)", "매도 (팔래)"], horizontal=True)
                price = st.number_input("희망 가격 (달러)", min_value=1, max_value=50, step=1)
                quantity = st.number_input("수량 (주)", min_value=1, max_value=50, step=1)
                
                # 제출 버튼
                submitted = st.form_submit_button("주문 전송")
                
                if submitted:
                    # 간단한 오류 방지 (돈이나 주식이 없는데 주문하는 것 막기)
                    if order_type == "매수 (살래)" and (price * quantity) > cash:
                        st.error(f"보유 현금이 부족합니다! (필요 현금: ${price * quantity})")
                    elif order_type == "매도 (팔래)" and quantity > shares:
                        st.error(f"보유 주식이 부족합니다! (현재 보유: {shares}주)")
                    else:
                        # 통과하면 구글 시트 [주문장] 탭에 한 줄 추가하기
                        clean_type = "매수" if "매수" in order_type else "매도"
                        new_row = [current_round, student_id, clean_type, price, quantity]
                        ws_orders.append_row(new_row)
                        
                        st.success(f"✅ {clean_type} 주문 접수 완료! (가격: ${price}, 수량: {quantity}주)")
                        
        else:
            st.warning("등록되지 않은 학번입니다. 오타가 없는지 확인해주세요.")
            
    except ValueError:
        st.error("학번은 숫자만 입력해주세요.")