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
                st.sidebar.error(f"❌ 저장 실패: {e}")

# --- 5. 메인 대시보드 ---
st.title("💰 지호 & 정희 통합 가계부")
tab1, tab2, tab3 = st.tabs(["📊 월간 분석 & 수정", "🔍 카테고리 상세", "📅 연간 리포트"])

# 표 서식 공통 설정 (날짜 시간 삭제, 콤마 표시)
col_config = {
    "날짜": st.column_config.DateColumn(format="YYYY-MM-DD"),
    "수입": st.column_config.NumberColumn(format="%,d"),
    "지출": st.column_config.NumberColumn(format="%,d")
}

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        all_months = sorted(df['연월'].unique(), reverse=True)
        sel_m = st.selectbox("📅 월 선택", all_months)
        m_df = df[df['연월'] == sel_m].copy()
        
        # 지표 표시
        c1, c2, c3 = st.columns(3)
        c1.metric("월 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("월 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        gc1, gc2 = st.columns(2)
        with gc1:
            if m_df['지출'].sum() > 0:
                st.plotly_chart(px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="지출 비중 (대분류)"), use_container_width=True)
        with gc2:
            if m_df['수입'].sum() > 0:
                st.plotly_chart(px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', hole=0.3, title="수입 비중 (소분류)"), use_container_width=True)
        
        # 내역 수정 기능 통합
        st.subheader(f"📝 {sel_m} 상세 내역 확인 및 수정")
        st.caption("표 안의 내용을 클릭해 수정하거나, 행을 선택해 삭제할 수 있습니다.")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.date # 시간 삭제

        edited_df = st.data_editor(
            m_df_edit, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config=col_config,
            hide_index=True
        )
        
        if st.button("💾 변경사항 시트에 반영"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            
            # 수정된 데이터 날짜 포맷 복구
            edited_df_save = edited_df.copy()
            edited_df_save['날짜'] = pd.to_datetime(edited_df_save['날짜']).dt.strftime('%Y-%m-%d')
            
            final_df = pd.concat([other_data, edited_df_save], ignore_index=True)
            try:
                conn.update(spreadsheet=SHEET_URL, data=final_df)
                st.success("✅ 시트에 성공적으로 반영되었습니다!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 실패: {e}")

with tab2:
    if not df.empty:
        st.subheader(f"🔍 {sel_m} 카테고리별 정밀 분석")
        
        # 1. 대분류별 지출 요약
        exp_only = m_df[m_df['지출'] > 0].copy()
        if not exp_only.empty:
            m_sum = exp_only.groupby('대분류')['지출'].sum().sort_values(ascending=False).reset_index()
            
            sc1, sc2 = st.columns([1, 2])
            with sc1:
                st.write("**항목별 지출 합계**")
                st.dataframe(
                    m_sum, 
                    column_config={"지출": st.column_config.NumberColumn(format="%,d")},
                    hide_index=True,
                    use_container_width=True
                )
            
            with sc2:
                # 2. 대분류 클릭/선택 시 소분류 드릴다운
                selected_cat = st.selectbox("상세 정보를 볼 대분류를 선택하세요", m_sum['대분류'].unique())
                drill_df = exp_only[exp_only['대분류'] == selected_cat]
                
                fig = px.pie(
                    drill_df, 
                    values='지출', 
                    names='소분류', 
                    title=f"'{selected_cat}' 항목의 소분류 비중",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("이달에 기록된 지출 내역이 없습니다.")

with tab3:
    if not df.empty:
        st.subheader("📅 연간 추이 리포트")
        df['월'] = df['날짜'].dt.strftime('%m월')
        year_sum = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['수입'], name='수입', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['지출'], name='지출', marker_color='#ff7f0e'))
        fig.update_layout(barmode='group', template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        st.subheader("📈 연간 카테고리별 누적 지출")
        cat_trend = df[df['지출'] > 0].groupby(['월', '대분류'])['지출'].sum().reset_index()
        fig2 = px.bar(cat_trend, x='월', y='지출', color='대분류', title="월별 지출 구성", text_auto='.2s')
        fig2.update_layout(template="plotly_white", barmode='stack')
        st.plotly_chart(fig2, use_container_width=True)
