import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# 팀장님 구글 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo/edit#gid=0"

# --- 2. 보안 설정 (비밀번호: 0614) ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔐 지호 & 정희 가계부")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if pwd == "0614":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# --- 3. 구글 시트 연결 및 데이터 로드 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl=0으로 설정하여 캐시 없이 실시간 데이터를 읽어옵니다.
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        
        # 컬럼명 양끝 공백 제거 (인식 오류 방지)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 데이터가 비어있는 경우 빈 틀 생성
        if df.empty:
            return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

        # 데이터 정제
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ 시트 읽기 오류: {e}")
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

df = load_data()

# 가계부 카테고리 설정
config = {
    "users": ["지호", "정희"],
    "categories": {
        "식비": ["점심", "외식", "식재료", "배달", "간식/커피"],
        "주거/생활": ["월세/대출이자", "관리비", "공과금", "보험료", "가구/가전"],
        "교통/차량": ["대중교통", "주유", "통행료", "차량유지비"],
        "투자/수입": ["월급", "실현손익", "배당금", "기타수입"],
        "교육/육아": ["학원비", "아이용품", "도서"],
        "꾸밈비": ["의류", "미용", "잡화"],
        "의료비": ["병원", "약국", "영양제"],
        "취미/여가": ["문화생활", "정기결제", "여행"],
        "기타": ["경조사", "기타"]
    }
}

# [상단 레이아웃]
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title("💰 지호 & 정희 구글 통합 가계부 💰")

# --- 4. 사이드바 입력창 ---
st.sidebar.header("➕ 신규 내역 입력")
with st.sidebar.form("input_form", clear_on_submit=True):
    d_in = st.date_input("날짜", datetime.now())
    u_in = st.selectbox("결제자", config["users"])
    m_in = st.selectbox("대분류", list(config["categories"].keys()))
    s_in = st.selectbox("소분류", config["categories"][m_in])
    item = st.text_input("상세 내역")
    inc = st.number_input("수입", min_value=0, step=1000)
    exp = st.number_input("지출", min_value=0, step=1000)
    
    if st.form_submit_button("구글 시트에 저장"):
        new_row = pd.DataFrame([[d_in.strftime('%Y-%m-%d'), m_in, s_in, item, int(inc), int(exp), u_in]], 
                                columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
        # 기존 데이터와 합쳐서 구글 시트 업데이트
        updated_df = pd.concat([df, new_row], ignore_index=True)
        updated_df['날짜'] = updated_df['날짜'].dt.strftime('%Y-%m-%d')
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        st.sidebar.success("✅ 저장 성공!")
        st.rerun()

# --- 5. 메인 화면 (탭 구성) ---
tab1, tab2, tab3 = st.tabs(["📊 월별 분석", "🔍 분류별 통계", "📅 연간 요약"])

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        all_months = sorted(df['연월'].unique(), reverse=True)
        sel_m = st.selectbox("📅 월 선택", all_months, key="sel_month")
        
        m_df = df[df['연월'] == sel_m].copy()
        
        # 상단 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("월 총 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("월 총 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("남은 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()

        # 그래프 섹션 (표 위쪽)
        gc1, gc2 = st.columns(2)
        with gc1:
            exp_data = m_df[m_df['지출'] > 0].groupby('대분류')['지출'].sum().reset_index()
            if not exp_data.empty:
                st.plotly_chart(px.pie(exp_data, values='지출', names='대분류', title="📉 지출 비중", hole=0.3), use_container_width=True)
        with gc2:
            inc_data = m_df[m_df['수입'] > 0].groupby('소분류')['수입'].sum().reset_index()
            if not inc_data.empty:
                st.plotly_chart(px.pie(inc_data, values='수입', names='소분류', title="📈 수입 구성", hole=0.3), use_container_width=True)

        st.divider()
        st.subheader("📝 상세 내역 수정")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
        
        # 데이터 에디터
        edited_df = st.data_editor(
            m_df_edit.sort_values('날짜', ascending=False),
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "수입": st.column_config.NumberColumn("수입", format="%,d"),
                "지출": st.column_config.NumberColumn("지출", format="%,d")
            },
            key="month_editor"
        )

        # 상단 우측 저장 버튼 동작
        with col_t2:
            st.write("")
            if st.button("💾 수정사항 저장", use_container_width=True):
                other_months = df[df['연월'] != sel_m].drop(columns
