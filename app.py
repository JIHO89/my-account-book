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

# 가계부 데이터 로드
@st.cache_data(ttl=0)
def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=0, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['수입'] = pd.to_numeric(df['수입'], errors='coerce').fillna(0).astype(int)
        df['지출'] = pd.to_numeric(df['지출'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame(columns=['날짜', '대분류', '소분류', '항목', '수입', '지출', '결제자'])

# 자산 현황 데이터 로드
@st.cache_data(ttl=0)
def load_asset_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="자산현황", ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            return pd.DataFrame(columns=['날짜', '소유자', '자산항목', '금액'])
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0).astype(int)
        return df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame(columns=['날짜', '소유자', '자산항목', '금액'])

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
                conn.update(spreadsheet=SHEET_URL, worksheet=0, data=updated_df)
                st.sidebar.success("✅ 저장 성공!")
                st.cache_data.clear() 
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ 저장 실패: {e}")

# --- 5. 메인 대시보드 ---
st.title("💰 지호 & 정희 통합 가계부")
tab1, tab2, tab3, tab4 = st.tabs(["📊 월간 분석 & 수정", "🔍 카테고리 상세", "📅 연간 리포트", "📈 자산 추이"])

col_config = {
    "날짜": st.column_config.DateColumn(format="YYYY-MM-DD"),
    "수입": st.column_config.NumberColumn(format="%,d"),
    "지출": st.column_config.NumberColumn(format="%,d")
}

PASTEL_INC, PASTEL_EXP = "#AEC6CF", "#FFB347"

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
            if m_df['지출'].sum() > 0:
                fig = px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, title="지출 비중", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(hovertemplate='%{label}<br>%{value:,.0f}원'); st.plotly_chart(fig, use_container_width=True)
        with gc2:
            if m_df['수입'].sum() > 0:
                fig = px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', hole=0.3, title="수입 비중", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(hovertemplate='%{label}<br>%{value:,.0f}원'); st.plotly_chart(fig, use_container_width=True)
        st.subheader(f"📝 {sel_m} 상세 내역")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.date
        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic", column_config=col_config, hide_index=True)
        if st.button("💾 변경사항 반영"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            edited_df_save = edited_df.copy()
            edited_df_save['날짜'] = pd.to_datetime(edited_df_save['날짜']).dt.strftime('%Y-%m-%d')
            final_df = pd.concat([other_data, edited_df_save], ignore_index=True)
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=0, data=final_df)
                st.success("✅ 업데이트 완료!"); st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 실패: {e}")

with tab2:
    if not df.empty:
        exp_only = m_df[m_df['지출'] > 0].copy()
        if not exp_only.empty:
            m_sum = exp_only.groupby('대분류')['지출'].sum().sort_values(ascending=False).reset_index()
            sc1, sc2 = st.columns([1, 2])
            with sc1:
                st.dataframe(m_sum, column_config={"지출": st.column_config.NumberColumn(format="%,d")}, hide_index=True, use_container_width=True)
            with sc2:
                selected_cat = st.selectbox("대분류 선택", m_sum['대분류'].unique())
                fig = px.pie(exp_only[exp_only['대분류'] == selected_cat], values='지출', names='소분류', title=f"'{selected_cat}' 소분류", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(hovertemplate='%{label}<br>%{value:,.0f}원'); st.plotly_chart(fig, use_container_width=True)

with tab3:
    if not df.empty:
        st.subheader("📊 2026 누적 현황")
        ac1, ac2, ac3 = st.columns(3)
        ac1.metric("총 수입", f"{df['수입'].sum():,}원"); ac2.metric("총 지출", f"{df['지출'].sum():,}원"); ac3.metric("누적 잔액", f"{(df['수입'].sum()-df['지출'].sum()):,}원")
        st.divider()
        df['월'] = df['날짜'].dt.strftime('%m월')
        year_sum = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['수입'], name='수입', marker_color=PASTEL_INC, hovertemplate='%{y:,.0f}원'))
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['지출'], name='지출', marker_color=PASTEL_EXP, hovertemplate='%{y:,.0f}원'))
        fig.update_layout(barmode='group', template="plotly_white"); fig.update_yaxes(tickformat=","); st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("📈 우리가 모은 돈 (총 자산 추이)")
    asset_df = load_asset_data()
    
    with st.expander("➕ 이달의 자산 기록하기", expanded=True):
        with st.form("asset_input_form", clear_on_submit=False):
            a_date = st.date_input("기준일", datetime.now().replace(day=1))
            st.caption("단위: 원 (숫자만 입력)")
            c_j, c_h, c_s, c_c = st.columns(4)
            with c_j:
                st.markdown("**👦 지호**")
                j_1, j_p, j_2, j_3, j_4, j_5 = st.number_input("예적금", key='j1'), st.number_input("연금저축", key='jp'), st.number_input("청약", key='j2'), st.number_input("보통예금", key='j3'), st.number_input("국내주식", key='j4'), st.number_input("해외주식", key='j5')
            with c_h:
                st.markdown("**👩 정희**")
                h_1, h_p, h_2, h_3, h_4, h_5 = st.number_input("예적금", key='h1'), st.number_input("연금저축", key='hp'), st.number_input("청약", key='h2'), st.number_input("청년도약계좌", key='h3'), st.number_input("보통예금", key='h4'), st.number_input("국내주식", key='h5')
            with c_s:
                st.markdown("**👶 수인**")
                s_1, s_2 = st.number_input("수인 국내주식", key='s1'), st.number_input("수인 해외주식", key='s2')
            with c_c:
                st.markdown("**🏠 공통**")
                c_1 = st.number_input("보증금/기타", key='c1')
            
            if st.form_submit_button("💾 자산 현황 저장"):
                d_str = a_date.strftime('%Y-%m-%d')
                new_rows = [[d_str, '지호', '예적금', j_1], [d_str, '지호', '연금저축', j_p], [d_str, '지호', '청약', j_2], [d_str, '지호', '보통예금', j_3], [d_str, '지호', '국내주식', j_4], [d_str, '지호', '해외주식', j_5],
                            [d_str, '정희', '예적금', h_1], [d_str, '정희', '연금저축', h_p], [d_str, '정희', '청약', h_2], [d_str, '정희', '청년도약계좌', h_3], [d_str, '정희', '보통예금', h_4], [d_str, '정희', '국내주식', h_5],
                            [d_str, '수인', '국내주식', s_1], [d_str, '수인', '해외주식', s_2], [d_str, '공통', '보증금/기타', c_1]]
                new_df = pd.DataFrame(new_rows, columns=['날짜', '소유자', '자산항목', '금액'])
                try:
                    if not asset_df.empty:
                        # 원본 asset_df를 안전하게 복사하여 처리
                        temp_asset_df = asset_df.copy()
                        temp_asset_df['날짜'] = temp_asset_df['날짜'].dt.strftime('%Y-%m-%d')
                        temp_asset_df = temp_asset_df[temp_asset_df['날짜'] != d_str]
                        final_asset_df = pd.concat([temp_asset_df, new_df], ignore_index=True)
                    else: 
                        final_asset_df = new_df
                    conn.update(spreadsheet=SHEET_URL, worksheet="자산현황", data=final_asset_df)
                    st.success("✅ 자산 기록 완료!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 저장 실패: {e}")

    if not asset_df.empty:
        st.divider()
        trend_copy = asset_df.copy()
        trend_copy['연월'] = trend_copy['날짜'].dt.strftime('%Y-%m')
        monthly_trend = trend_copy.groupby('연월')['금액'].sum().reset_index()
        
        # --- 현금화 및 비현금화 자산 계산 로직 ---
        latest_date = asset_df['날짜'].max()
        latest_df = asset_df[asset_df['날짜'] == latest_date].copy()
        
        # 1. 현금화 가능 항목
        liquid_items = ['보증금/기타', '보통예금', '국내주식', '해외주식', '예적금']
        liquid_mask = latest_df['자산항목'].isin(liquid_items)
        suin_mask = (latest_df['소유자'] == '수인') & (latest_df['자산항목'].isin(['국내주식', '해외주식']))
        
        liquid_total = latest_df[liquid_mask & ~suin_mask]['금액'].sum()
        
        # 2. 비현금화 가능 항목 (전체 - 현금화가능)
        total_latest = latest_df['금액'].sum()
        non_liquid_total = total_latest - liquid_total
        
        # --- 상단 지표 표시 (3단 구성) ---
        ac1, ac2, ac3 = st.columns(3)
        ac1.metric(label=f"💎 총 자산 ({latest_date.strftime('%Y-%m-%d')})", value=f"{total_latest:,}원")
        ac2.metric(label="💸 현금화 가능 금액", value=f"{liquid_total:,}원", help="보증금, 보통예금, 예적금, 주식(수인 제외)")
        ac3.metric(label="🔒 비현금화 자산", value=f"{non_liquid_total:,}원", help="연금저축, 청약, 청년도약계좌, 수인 주식")
        
        # 그래프
        fig_trend = px.area(monthly_trend, x='연월', y='금액', markers=True, title="월별 자산 성장 추이")
        fig_trend.update_traces(line_color='#2ca02c', fillcolor='rgba(44, 160, 44, 0.2)', hovertemplate='%{x}<br>%{y:,.0f}원')
        fig_trend.update_xaxes(type='category', title="조회 월") 
        fig_trend.update_yaxes(tickformat=","); fig_trend.update_layout(template="plotly_white")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        st.subheader("📋 가장 최근 자산 상세 요약")
        pivot_df = latest_df.pivot_table(index='자산항목', columns='소유자', values='금액', aggfunc='sum').fillna(0)
        pivot_df['총계'] = pivot_df.sum(axis=1)
        st.dataframe(pivot_df.style.format("{:,.0f}원"), use_container_width=True)
