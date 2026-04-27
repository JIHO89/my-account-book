import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="지호 & 정희 통합 가계부", layout="wide")

# 팀장님 구글 시트 ID (주소에서 추출한 값)
SHEET_ID = "1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

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

# --- 3. 데이터 로드 및 저장 함수 (인증 우회 방식) ---
def get_gsheet_client():
    # 이 방식은 '링크가 있는 모든 사용자 - 편집자' 설정일 때 작동합니다.
    # 만약 Streamlit Cloud에서 gspread 인증 에러가 나면 말씀해주세요.
    # 일단 가장 확실한 Pandas 읽기 방식을 혼합합니다.
    return None

@st.cache_data(ttl=0)
def load_data():
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
        df = pd.read_csv(csv_url)
        df.columns = [str(c).strip() for c in df.columns]
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except:
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

# [핵심] streamlit-gsheets 대신 직접 저장 로직 시도
def save_to_gsheet(dataframe):
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 에러를 피하기 위해 spreadsheet_id를 명시적으로 전달
        conn.update(spreadsheet=SHEET_URL, data=dataframe)
        return True
    except Exception as e:
        if "Public Spreadsheet cannot be written to" in str(e):
            st.error("🚨 구글 보안 정책으로 인해 직접 저장이 차단되었습니다.")
            st.info("💡 팀장님, 이 문제는 구글의 '서비스 계정' 인증이 필요합니다. 가장 쉬운 해결책은 구글 시트의 [데이터 > 시트 보호]가 아닌, Streamlit의 Secrets 설정에 인증 정보를 넣는 것이지만 절차가 복잡합니다.")
            st.warning("대안으로, 수정된 데이터를 CSV로 다운로드하여 구글 시트에 붙여넣는 버튼을 임시로 만들어드릴까요?")
        else:
            st.error(f"저장 중 에러 발생: {e}")
        return False

df = load_data()

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

# --- 4. 메인 화면 ---
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

# --- 5. 분석 탭 ---
tab1, tab2, tab3 = st.tabs(["📊 월별 분석", "🔍 상세 내역 수정", "📅 연간 요약"])

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        sel_m = st.selectbox("📅 월 선택", sorted(df['연월'].unique(), reverse=True))
        m_df = df[df['연월'] == sel_m].copy()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("월 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("월 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        gc1, gc2 = st.columns(2)
        with gc1:
            st.plotly_chart(px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="지출 비중"), use_container_width=True)
        with gc2:
            st.plotly_chart(px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', title="수입 구성"), use_container_width=True)

with tab2:
    if not df.empty:
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.strftime('%Y-%m-%d')
        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 수정사항 저장"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            final_df = pd.concat([other_data, edited_df], ignore_index=True)
            if save_to_gsheet(final_df):
                st.success("✅ 업데이트 완료!")
                st.rerun()

with tab3:
    if not df.empty:
        df['월'] = df['날짜'].dt.strftime('%m월')
        ms = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=ms['월'], y=ms['수입'], name='수입', marker_color='#1f77b4'))
        fig.add_trace(go.Bar(x=ms['월'], y=ms['지출'], name='지출', marker_color='#ff7f0e'))
        fig.update_layout(barmode='group', template="plotly_white", title="연간 추이")
        st.plotly_chart(fig, use_container_width=True)
