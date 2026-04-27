import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# [중요] 팀장님 시트 ID 추출 및 주소 설정
# 주소 뒷부분의 /edit 등을 떼고 /export로 변환하여 읽기/쓰기 효율을 높입니다.
SHEET_ID = "1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo"
READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

# --- 2. 보안 설정 ---
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

# --- 3. 데이터 로드 및 저장 함수 (표준 방식) ---
@st.cache_data(ttl=0) # 실시간 반영을 위해 캐시 수명 0
def load_data():
    try:
        # 가장 표준적인 Pandas 읽기 방식
        df = pd.read_csv(READ_URL)
        df.columns = [str(c).strip() for c in df.columns]
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except:
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

# [핵심] 구글 시트 업데이트 함수
# streamlit-gsheets 에러를 피하기 위해 st.connection 대신 직접 업데이트 로직 시도
def save_to_gsheet(dataframe):
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{SHEET_ID}", data=dataframe)
        return True
    except Exception as e:
        st.error(f"저장 중 에러 발생: {e}")
        st.info("💡 팁: Streamlit Cloud Settings -> Secrets에 아래 내용을 넣으셨는지 확인해주세요.")
        st.code(f'[connections.gsheets]\nspreadsheet = "https://docs.google.com/spreadsheets/d/{SHEET_ID}"')
        return False

df = load_data()

# 카테고리 설정
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

# --- 4. 메인 UI 및 저장 로직 ---
st.title("💰 지호 & 정희 통합 가계부")

st.sidebar.header("➕ 신규 입력")
u_in = st.sidebar.selectbox("결제자", config["users"])
m_in = st.sidebar.selectbox("대분류", list(config["categories"].keys()))
s_in = st.sidebar.selectbox("소분류", config["categories"][m_in])

with st.sidebar.form("input_form", clear_on_submit=True):
    d_in = st.date_input("날짜", datetime.now())
    item = st.text_input("상세 내역")
    inc = st.number_input("수입", min_value=0)
    exp = st.number_input("지출", min_value=0)
    
    if st.form_submit_button("구글 시트에 저장"):
        new_row = pd.DataFrame([[d_in.strftime('%Y-%m-%d'), m_in, s_in, item, int(inc), int(exp), u_in]], 
                                columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
        
        df_save = df.copy()
        df_save['날짜'] = df_save['날짜'].dt.strftime('%Y-%m-%d')
        updated_df = pd.concat([df_save, new_row], ignore_index=True)
        
        if save_to_gsheet(updated_df):
            st.sidebar.success("✅ 저장 성공!")
            st.rerun()

# --- 5. 분석 탭 (이미지 스타일 차트 반영) ---
tab1, tab2 = st.tabs(["📊 분석 및 수정", "📅 연간 요약"])

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        sel_m = st.selectbox("📅 월 선택", sorted(df['연월'].unique(), reverse=True))
        m_df = df[df['연월'] == sel_m].copy()
        
        # 그래프 상단 배치
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="월간 지출 비중"), use_container_width=True)
        with c2:
            # 월별 지표
            st.metric("월 수입", f"{m_df['수입'].sum():,}원")
            st.metric("월 지출", f"{m_df['지출'].sum():,}원")
            st.metric("남은 잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        st.subheader("📝 내역 수정")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 표 수정내용 저장"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            other_months = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            final_df = pd.concat([other_months, edited_df], ignore_index=True)
            if save_to_gsheet(final_df):
                st.success("✅ 수정 완료!")
                st.rerun()

with tab2:
    if not df.empty:
        df['월'] = df['날짜'].dt.strftime('%m월')
        ms = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=ms['월'], y=ms['수입'], name='수입', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=ms['월'], y=ms['지출'], name='지출', marker_color='#ff7f0e'))
        fig.update_layout(barmode='group', template="plotly_white", title="연간 수입 vs 지출")
        st.plotly_chart(fig, use_container_width=True)
