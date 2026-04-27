import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# --- 2. 구글 시트 연결 (Service Account 자동 인증) ---
# Secrets에 [connections.gsheets] 설정이 정확하면 자동으로 연결됩니다.
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        # 인증된 상태이므로 전체 데이터를 읽어옵니다.
        df = conn.read(ttl=0)
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

# 데이터 불러오기
df = load_data()

# --- 3. 보안 및 설정 ---
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

# --- 4. 사이드바: 데이터 입력 ---
st.sidebar.header("➕ 신규 내역 입력")
u_in = st.sidebar.selectbox("결제자", config["users"])
m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

with st.sidebar.form("input_form", clear_on_submit=True):
    d_in = st.date_input("날짜", datetime.now())
    item = st.text_input("상세 내역")
    inc = st.number_input("수입 금액", min_value=0, step=1000)
    exp = st.number_input("지출 금액", min_value=0, step=1000)
    
    if st.form_submit_button("구글 시트에 저장"):
        if not item:
            st.error("내용을 입력해 주세요.")
        else:
            new_row = pd.DataFrame([[d_in.strftime('%Y-%m-%d'), m_in, s_in, item, int(inc), int(exp), u_in]], 
                                    columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
            
            # 기존 데이터와 합치기 (날짜 포맷 통일)
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            updated_df = pd.concat([df_all, new_row], ignore_index=True)
            
            try:
                # [자동화 핵심] 서비스 계정 권한으로 시트 업데이트
                conn.update(data=updated_df)
                st.sidebar.success("✅ 저장 완료!")
                st.cache_data.clear() # 캐시 삭제 후 새로고침
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ 저장 실패: {e}")

# --- 5. 메인 화면: 분석 및 수정 ---
st.title("💰 지호 & 정희 통합 가계부")
tab1, tab2, tab3 = st.tabs(["📊 월별 분석", "🔍 상세 내역 수정", "📅 연간 요약"])

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        sel_m = st.selectbox("📅 월 선택", sorted(df['연월'].unique(), reverse=True))
        m_df = df[df['연월'] == sel_m].copy()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("월 총 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("월 총 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("남은 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        gc1, gc2 = st.columns(2)
        with gc1:
            st.plotly_chart(px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="📉 지출 비중"), use_container_width=True)
        with gc2:
            st.plotly_chart(px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', hole=0.3, title="📈 수입 구성"), use_container_width=True)

with tab2:
    if not df.empty:
        st.subheader(f"📝 {sel_m} 내역 편집")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
        
        # 표에서 직접 수정 가능
        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 변경사항 구글 시트에 즉시 반영"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            # 현재 월 제외 데이터 + 현재 월 수정 데이터
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            final_df = pd.concat([other_data, edited_df], ignore_index=True)
            
            try:
                conn.update(data=final_df)
                st.success("✅ 구글 시트 업데이트 완료!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 실패: {e}")

with tab3:
    if not df.empty:
        st.subheader("📅 연간 수입/지출 추이")
        df['월'] = df['날짜'].dt.strftime('%m월')
        ms = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=ms['월'], y=ms['수입'], name='수입', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=ms['월'], y=ms['지출'], name='지출', marker_color='#ff7f0e'))
        fig.update_layout(barmode='group', template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
