import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# --- 2. 구글 시트 연결 설정 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
        
        # 데이터 정제
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ 데이터 로드 오류: {e}")
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

df = load_data()

# --- 3. 로그인 보안 ---
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

# 카테고리 구성
config = {
    "users": ["지호", "정희"],
    "categories": {
        "투자/수입": ["월급", "실현손익", "배당금", "기타수입"],
        "식비": ["점심", "외식", "식재료", "배달", "간식/커피"],
        "주거/생활": ["월세/대출이자", "관리비", "공과금", "보험료", "가구/가전"],
        "교통/차량": ["대중교통", "주유", "통행료", "차량유지비"],
        "교육/육아": ["학원비", "아이용품", "도서"],
        "꾸밈비": ["의류", "미용", "잡화"],
        "의료비": ["병원", "약국", "영양제"],
        "취미/여가": ["문화생활", "정기결제", "여행"],
        "기타": ["경조사", "기타"]
    }
}

# --- 4. 사이드바: 입력란 ---
st.sidebar.header("➕ 내역 추가")
u_in = st.sidebar.selectbox("결제자", config["users"])
m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

with st.sidebar.form("input_form", clear_on_submit=True):
    d_in = st.date_input("날짜", datetime.now())
    item = st.text_input("상세 항목")
    inc = st.number_input("수입(원)", min_value=0, step=1000)
    exp = st.number_input("지출(원)", min_value=0, step=1000)
    
    if st.form_submit_button("시트에 저장"):
        if not item:
            st.warning("상세 내역을 입력하세요.")
        else:
            new_row = pd.DataFrame([[d_in.strftime('%Y-%m-%d'), m_in, s_in, item, int(inc), int(exp), u_in]], 
                                    columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
            
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            updated_df = pd.concat([df_all, new_row], ignore_index=True)
            
            try:
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.sidebar.success("✅ 저장 성공!")
                st.cache_data.clear() 
                st.rerun()
            except Exception as e:
                # 여기서 문법 에러가 나지 않도록 따옴표를 정확히 닫았습니다.
                st.sidebar.error(f"❌ 저장 실패: {e}")

# --- 5. 메인 대시보드 ---
st.title("💰 지호 & 정희 통합 가계부")
tab1, tab2, tab3 = st.tabs(["📊 월간 분석", "🔍 내역 수정", "📅 연간 리포트"])

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        sel_m = st.selectbox("📅 조회할 월을 선택하세요", sorted(df['연월'].unique(), reverse=True))
        m_df = df[df['연월'] == sel_m].copy()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("월 총 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("월 총 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("이달의 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        gc1, gc2 = st.columns(2)
        with gc1:
            if m_df['지출'].sum() > 0:
                st.plotly_chart(px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="지출 비중 (대분류)"), use_container_width=True)
        with gc2:
            if m_df['수입'].sum() > 0:
                st.plotly_chart(px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', hole=0.3, title="수입 비중 (소분류)"), use_container_width=True)
        
        # 월간 분석 하단에 상세 표 노출
        st.subheader(f"📄 {sel_m} 상세 내역")
        st.dataframe(m_df.drop(columns=['연월']), use_container_width=True, hide_index=True)

with tab2:
    if not df.empty:
        st.subheader(f"📝 {sel_m} 데이터 수정 및 삭제")
        st.info("아래 표를 직접 클릭하여 수정하거나, 행을 선택해 삭제할 수 있습니다.")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
        
        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 시트에 반영 (수정/삭제 완료)"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            final_df = pd.concat([other_data, edited_df], ignore_index=True)
            
            try:
                conn.update(spreadsheet=SHEET_URL, data=final_df)
                st.success("✅ 시트가 업데이트되었습니다!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 실패: {e}")

with tab3:
    if not df.empty:
        st.subheader("📊 2026년 월별 총 흐름")
        df['월'] = df['날짜'].dt.strftime('%m월')
        year_sum = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        
        # 월별 수입/지출 막대 그래프
        fig = go.Figure()
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['수입'], name='총 수입', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['지출'], name='총 지출', marker_color='#ff7f0e'))
        fig.update_layout(barmode='group', template="plotly_white", margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        # 대분류별 지출 누적 추이 차트 (팀장님이 원하시던 그래프)
        st.subheader("📈 연간 대분류별 지출 누적 추이")
        exp_df = df[df['지출'] > 0].copy()
        if not exp_df.empty:
            cat_trend = exp_df.groupby(['월', '대분류'])['지출'].sum().reset_index()
            fig2 = px.bar(cat_trend, x='월', y='지출', color='대분류', title="월별 지출 구성", text_auto='.2s')
            fig2.update_layout(template="plotly_white", barmode='stack')
            st.plotly_chart(fig2, use_container_width=True)
