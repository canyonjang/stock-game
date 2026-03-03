import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import random
import time

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
status_data = ws_status.get_all_records()
current_round = int(status_data[0]['현재라운드'])
fair_value = int(status_data[0]['주식적정가치'])

assets_data = ws_assets.get_all_records()
df_assets = pd.DataFrame(assets_data)

orders_data = ws_orders.get_all_records()
df_orders = pd.DataFrame(orders_data)
df_current_orders = df_orders[df_orders['라운드'] == current_round] if not df_orders.empty else pd.DataFrame()

# ==========================================
# 🏆 게임 종료 시 (11라운드) 화면: 최종 랭킹보드
# ==========================================
if current_round > 10:
    st.title("🏆 주식 매매 게임 최종 결과 발표 🏆")
    st.write("10라운드의 모든 거래가 종료되었습니다. 가상 주식의 가치는 이제 **0원(휴지조각)**입니다.")
    st.write("오직 수중에 남은 **'현금'**만이 여러분의 최종 수익입니다!")
    st.balloons()
    st.write("---")
    
    # 순위 계산 (보유 현금 기준 내림차순 정렬)
    df_rank = df_assets.copy()
    df_rank = df_rank.sort_values(by='보유현금', ascending=False).reset_index(drop=True)
    df_rank.index = df_rank.index + 1 # 1등부터 시작하도록 인덱스 조정
    df_rank = df_rank[['이름', '학번', '보유현금', '보유주식수']]
    df_rank.columns = ['이름', '학번', '최종 수익(달러)', '휴지조각이 된 주식(주)']
    
    # 시상대 (1, 2, 3등 강조)
    st.subheader("🎉 명예의 전당 🎉")
    col1, col2, col3 = st.columns(3)
    if len(df_rank) >= 1:
        col1.success(f"🥇 1등: {df_rank.iloc[0]['이름']} ({df_rank.iloc[0]['최종 수익(달러)']}달러)")
    if len(df_rank) >= 2:
        col2.warning(f"🥈 2등: {df_rank.iloc[1]['이름']} ({df_rank.iloc[1]['최종 수익(달러)']}달러)")
    if len(df_rank) >= 3:
        col3.info(f"🥉 3등: {df_rank.iloc[2]['이름']} ({df_rank.iloc[2]['최종 수익(달러)']}달러)")
        
    st.write("---")
    
    # 전체 랭킹 표 보여주기
    st.subheader("전체 랭킹보드")
    st.dataframe(df_rank, use_container_width=True)
    
    st.write("---")
    
    # 다음 반 수업을 위한 초기화 버튼
    if st.button("🔄 새로운 클래스 게임 준비 (모든 데이터 초기화)", type="secondary"):
        with st.spinner("구글 시트를 초기화 중입니다..."):
            ws_status.update_acell('A2', 1)
            ws_status.update_acell('B2', 10)
            ws_status.update_acell('C2', 'X')
            
            df_assets['보유현금'] = 50
            df_assets['보유주식수'] = 5
            data_to_upload = [df_assets.columns.values.tolist()] + df_assets.values.tolist()
            ws_assets.clear()
            ws_assets.update(range_name='A1', values=data_to_upload)
            
            ws_orders.clear()
            ws_orders.update(range_name='A1', values=[['라운드', '학번', '주문구분', '희망가격', '주문수량']])
            
        st.success("초기화 완료! 1라운드부터 다시 시작합니다.")
        time.sleep(1)
        st.rerun()

    st.stop() # 게임 종료 화면이 뜨면 아래의 통상 거래 화면은 숨깁니다.

# ==========================================
# 📊 일반 라운드 (1~10라운드) 화면: 거래 통제소
# ==========================================
st.title("👨‍🏫 교사용 시장 통제소")
st.info(f"**현재 진행 중:** {current_round} 라운드 / **수학적 적정 가치:** {fair_value}달러")

col_b, col_s = st.columns(2)
with col_b:
    st.subheader("🔴 매수 (살래) 주문")
    if not df_current_orders.empty:
        st.dataframe(df_current_orders[df_current_orders['주문구분'] == '매수'])
with col_s:
    st.subheader("🔵 매도 (팔래) 주문")
    if not df_current_orders.empty:
        st.dataframe(df_current_orders[df_current_orders['주문구분'] == '매도'])

st.write("---")

col1, col2, col3 = st.columns(3)

# [버튼 1: 단일가 체결]
with col1:
    if st.button("🚨 1. 거래 체결하기", type="primary", use_container_width=True):
        if df_current_orders.empty:
            st.warning("체결할 주문이 없습니다.")
        else:
            buys = df_current_orders[df_current_orders['주문구분'] == '매수']
            sells = df_current_orders[df_current_orders['주문구분'] == '매도']
            
            all_prices = sorted(df_current_orders['희망가격'].unique())
            best_price, max_volume = 0, 0
            
            for p in all_prices:
                demand = buys[buys['희망가격'] >= p]['주문수량'].sum()
                supply = sells[sells['희망가격'] <= p]['주문수량'].sum()
                trade_volume = min(demand, supply)
                
                if trade_volume > max_volume:
                    max_volume = trade_volume
                    best_price = p
                    
            if max_volume > 0:
                assets_dict = df_assets.set_index('학번').to_dict('index')
                
                buys_sorted = buys.sort_values(by='희망가격', ascending=False)
                buy_vol_left = max_volume
                for _, row in buys_sorted.iterrows():
                    if buy_vol_left <= 0: break
                    if row['희망가격'] >= best_price:
                        fill_qty = min(row['주문수량'], buy_vol_left)
                        sid = row['학번']
                        if sid in assets_dict:
                            assets_dict[sid]['보유현금'] -= fill_qty * best_price
                            assets_dict[sid]['보유주식수'] += fill_qty
                        buy_vol_left -= fill_qty
                        
                sells_sorted = sells.sort_values(by='희망가격', ascending=True)
                sell_vol_left = max_volume
                for _, row in sells_sorted.iterrows():
                    if sell_vol_left <= 0: break
                    if row['희망가격'] <= best_price:
                        fill_qty = min(row['주문수량'], sell_vol_left)
                        sid = row['학번']
                        if sid in assets_dict:
                            assets_dict[sid]['보유현금'] += fill_qty * best_price
                            assets_dict[sid]['보유주식수'] -= fill_qty
                        sell_vol_left -= fill_qty

                updated_df = pd.DataFrame.from_dict(assets_dict, orient='index').reset_index().rename(columns={'index':'학번'})
                data_to_upload = [updated_df.columns.values.tolist()] + updated_df.values.tolist()
                
                ws_assets.clear()
                ws_assets.update(range_name='A1', values=data_to_upload)
                
                st.success(f"🎉 체결 완료! 균형 가격: {best_price}달러 / 거래량: {max_volume}주")
                time.sleep(2)
                st.rerun()
            else:
                st.error("매수-매도 가격이 맞지 않아 거래가 체결되지 않았습니다.")

# [버튼 2: 배당금 추첨]
with col2:
    if st.button("🎰 2. 배당금 추첨!", type="primary", use_container_width=True):
        with st.spinner("룰렛이 돌아갑니다..."):
            time.sleep(1)
            dividend = random.choice([0, 2])
            
            if dividend == 2:
                st.balloons()
                st.success("🎉 대박! 주당 2달러 배당금 당첨!")
                ws_status.update_acell('C2', 'O (당첨)')
                
                df_assets['보유현금'] = df_assets['보유현금'] + (df_assets['보유주식수'] * 2)
                data_to_upload = [df_assets.columns.values.tolist()] + df_assets.values.tolist()
                ws_assets.clear()
                ws_assets.update(range_name='A1', values=data_to_upload)
                
                time.sleep(2)
                st.rerun()
                
            else:
                st.error("💥 꽝입니다! 이번 라운드 배당금은 0원입니다.")
                ws_status.update_acell('C2', 'X (꽝)')
                time.sleep(2)
                st.rerun()

# [버튼 3: 다음 라운드 이동 및 종료]
with col3:
    # 10라운드일 때는 버튼 이름이 바뀝니다.
    if current_round == 10:
        btn_label = "🏁 3. 게임 종료 (최종 결과 보기)"
    else:
        btn_label = "⏭️ 3. 다음 라운드 시작"
        
    if st.button(btn_label, type="primary", use_container_width=True):
        ws_status.update_acell('A2', current_round + 1)
        if current_round < 10:
            ws_status.update_acell('B2', fair_value - 1)
            st.success(f"{current_round + 1}라운드가 시작되었습니다.")
        time.sleep(1)
        st.rerun()