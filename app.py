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

# 기존 가계부 데이터 로드 (첫 번째 시트)
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

# 신규: 자산 현황 데이터 로드
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

PASTEL_INC = "#AEC6CF" 
PASTEL_EXP = "#FFB347" 

with tab1:
    if not df.empty:
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        all_months = sorted(df['연월'].unique(), reverse=True)
        sel_m = st.selectbox("📅 월 선택", all_months)
        m_df = df[df['연월'] == sel_m].copy()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("월 수입", f"{m_df['수입'].sum():,}원")
        c2.metric("월 지출", f"{m_df['지출'].sum():,}원")
        c3.metric("잔액", f"{m_df['수입'].sum() - m_df['지출'].sum():,}원")
        
        st.divider()
        gc1, gc2 = st.columns(2)
        with gc1:
            if m_df['지출'].sum() > 0:
                pie_exp = px.pie(m_df[m_df['지출']>0], values='지출', names='대분류', hole=0.3, 
                                 title="지출 비중 (대분류)", color_discrete_sequence=px.colors.qualitative.Pastel)
                pie_exp.update_traces(hovertemplate='%{label}<br>%{value:,.0f}원')
                st.plotly_chart(pie_exp, use_container_width=True)
        with gc2:
            if m_df['수입'].sum() > 0:
                pie_inc = px.pie(m_df[m_df['수입']>0], values='수입', names='소분류', hole=0.3, 
                                 title="수입 비중 (소분류)", color_discrete_sequence=px.colors.qualitative.Pastel)
                pie_inc.update_traces(hovertemplate='%{label}<br>%{value:,.0f}원')
                st.plotly_chart(pie_inc, use_container_width=True)
        
        st.subheader(f"📝 {sel_m} 상세 내역 확인 및 수정")
        m_df_edit = m_df.drop(columns=['연월']).copy()
        m_df_edit['날짜'] = m_df_edit['날짜'].dt.date

        edited_df = st.data_editor(m_df_edit, use_container_width=True, num_rows="dynamic", column_config=col_config, hide_index=True)
        
        if st.button("💾 변경사항 시트에 반영"):
            df_all = df.copy()
            df_all['날짜'] = df_all['날짜'].dt.strftime('%Y-%m-%d')
            other_data = df_all[df_all['날짜'].str.slice(0, 7) != sel_m]
            edited_df_save = edited_df.copy()
            edited_df_save['날짜'] = pd.to_datetime(edited_df_save['날짜']).dt.strftime('%Y-%m-%d')
            final_df = pd.concat([other_data, edited_df_save], ignore_index=True)
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=0, data=final_df)
                st.success("✅ 시트에 반영되었습니다!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ 수정 실패: {e}")

with tab2:
    if not df.empty:
        st.subheader(f"🔍 {sel_m} 카테고리별 정밀 분석")
        exp_only = m_df[m_df['지출'] > 0].copy()
        if not exp_only.empty:
            m_sum = exp_only.groupby('대분류')['지출'].sum().sort_values(ascending=False).reset_index()
            sc1, sc2 = st.columns([1, 2])
            with sc1:
                st.write("**항목별 지출 합계**")
                st.dataframe(m_sum, column_config={"지출": st.column_config.NumberColumn(format="%,d")}, hide_index=True, use_container_width=True)
            with sc2:
                selected_cat = st.selectbox("상세 정보를 볼 대분류를 선택하세요", m_sum['대분류'].unique())
                drill_df = exp_only[exp_only['대분류'] == selected_cat]
                pie_drill = px.pie(drill_df, values='지출', names='소분류', title=f"'{selected_cat}' 소분류 비중", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                pie_drill.update_traces(hovertemplate='%{label}<br>%{value:,.0f}원')
                st.plotly_chart(pie_drill, use_container_width=True)

with tab3:
    if not df.empty:
        total_inc = df['수입'].sum()
        total_exp = df['지출'].sum()
        total_bal = total_inc - total_exp
        
        st.subheader("📊 2026년 전체 누적 현황")
        ac1, ac2, ac3 = st.columns(3)
        ac1.metric("연간 총 수입", f"{total_inc:,}원")
        ac2.metric("연간 총 지출", f"{total_exp:,}원")
        ac3.metric("가계부 누적 잔액", f"{total_bal:,}원")
        
        st.divider()
        
        st.subheader("📅 월별 수입 vs 지출 추이")
        df['월'] = df['날짜'].dt.strftime('%m월')
        year_sum = df.groupby('월')[['수입', '지출']].sum().reindex([f"{i:02d}월" for i in range(1, 13)]).fillna(0).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['수입'], name='수입', marker_color=PASTEL_INC, hovertemplate='%{x}: %{y:,.0f}원<extra></extra>'))
        fig.add_trace(go.Bar(x=year_sum['월'], y=year_sum['지출'], name='지출', marker_color=PASTEL_EXP, hovertemplate='%{x}: %{y:,.0f}원<extra></extra>'))
        fig.update_layout(barmode='group', template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(tickformat=",") 
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        st.subheader("📈 연간 카테고리별 누적 지출")
        cat_trend = df[df['지출'] > 0].groupby(['월', '대분류'])['지출'].sum().reset_index()
        fig2 = px.bar(cat_trend, x='월', y='지출', color='대분류', title="월별 지출 구성", text_auto=',', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(template="plotly_white", barmode='stack')
        fig2.update_yaxes(tickformat=",")
        fig2.update_traces(hovertemplate='%{x} - %{color}<br>%{y:,.0f}원')
        st.plotly_chart(fig2, use_container_width=True)

# 신규: 4. 자산 추이 탭
with tab4:
    st.subheader("📈 우리가 모은 돈 (총 자산 추이)")
    st.caption("매월 1일, 흩어져 있는 자산을 모아 기록하고 쑥쑥 자라나는 성장을 확인하세요!")
    
    asset_df = load_asset_data()
    
    # 자산 입력 폼 (이전에 입력한 값을 유지하도록 clear_on_submit=False 설정)
    with st.expander("➕ 이달의 자산 기록하기", expanded=True):
        with st.form("asset_input_form", clear_on_submit=False):
            # 매월 1일을 기본값으로 세팅
            a_date = st.date_input("기준일", datetime.now().replace(day=1))
            st.caption("단위: 원 (숫자만 입력하세요)")
            
            # 올려주신 엑셀 표와 동일한 구조
            c_j, c_h, c_s, c_c = st.columns(4)
            with c_j:
                st.markdown("**👦 지호**")
                j_1 = st.number_input("예적금/연금", step=100000, key='j1')
                j_2 = st.number_input("청약", step=100000, key='j2')
                j_3 = st.number_input("보통예금", step=100000, key='j3')
                j_4 = st.number_input("국내주식", step=100000, key='j4')
                j_5 = st.number_input("해외주식", step=100000, key='j5')
            with c_h:
                st.markdown("**👩 정희**")
                h_1 = st.number_input("예적금/연금", step=100000, key='h1')
                h_2 = st.number_input("청약", step=100000, key='h2')
                h_3 = st.number_input("청년도약계좌", step=100000, key='h3')
                h_4 = st.number_input("보통예금", step=100000, key='h4')
                h_5 = st.number_input("국내주식", step=100000, key='h5')
            with c_s:
                st.markdown("**👶 수인**")
                s_1 = st.number_input("국내주식", step=100000, key='s1')
                s_2 = st.number_input("해외주식", step=100000, key='s2')
            with c_c:
                st.markdown("**🏠 공통**")
                c_1 = st.number_input("보증금/기타", step=1000000, key='c1')
            
            if st.form_submit_button("💾 자산 현황 저장"):
                d_str = a_date.strftime('%Y-%m-%d')
                new_rows = [
                    [d_str, '지호', '예적금/연금저축', j_1], [d_str, '지호', '청약', j_2], [d_str, '지호', '보통예금', j_3], [d_str, '지호', '국내주식', j_4], [d_str, '지호', '해외주식', j_5],
                    [d_str, '정희', '예적금/연금저축', h_1], [d_str, '정희', '청약', h_2], [d_str, '정희', '청년도약계좌', h_3], [d_str, '정희', '보통예금', h_4], [d_str, '정희', '국내주식', h_5],
                    [d_str, '수인', '국내주식', s_1], [d_str, '수인', '해외주식', s_2],
                    [d_str, '공통', '보증금/기타', c_1]
                ]
                
                new_df = pd.DataFrame(new_rows, columns=['날짜', '소유자', '자산항목', '금액'])
                
                try:
                    if not asset_df.empty:
                        asset_df['날짜'] = asset_df['날짜'].dt.strftime('%Y-%m-%d')
                        # 같은 날짜에 다시 저장하면 기존 데이터를 덮어씌움
                        asset_df = asset_df[asset_df['날짜'] != d_str]
                        final_asset_df = pd.concat([asset_df, new_df], ignore_index=True)
                    else:
                        final_asset_df = new_df
                        
                    conn.update(spreadsheet=SHEET_URL, worksheet="자산현황", data=final_asset_df)
                    st.success("✅ 새로운 자산 기록이 멋지게 저장되었습니다!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 저장 실패: {e}")

    # 자산 대시보드 시각화
    if not asset_df.empty:
        st.divider()
        
        # 날짜별 총 자산 계산
        trend_df = asset_df.groupby('날짜')['금액'].sum().reset_index()
        trend_df['날짜_str'] = trend_df['날짜'].dt.strftime('%Y-%m')
        
        latest_date = trend_df['날짜'].max()
        latest_total = trend_df[trend_df['날짜'] == latest_date]['금액'].values[0]
        
        # 이전 달과 비교
        delta = 0
        if len(trend_df) > 1:
            prev_total = trend_df.sort_values(by='날짜', ascending=False).iloc[1]['금액']
            delta = latest_total - prev_total
            
        st.metric(label=f"💎 현재 우리 가족 총 자산 ({latest_date.strftime('%Y-%m-%d')} 기준)", 
                  value=f"{latest_total:,.0f}원", 
                  delta=f"{delta:,.0f}원 (지난 기록 대비)")
        
        st.subheader("🚀 2026년 자산 성장 그래프")
        fig_trend = px.area(trend_df, x='날짜_str', y='금액', markers=True, title="시간이 지날수록 불어나는 총액")
        fig_trend.update_traces(line_color='#2ca02c', fillcolor='rgba(44, 160, 44, 0.2)', hovertemplate='%{x}<br>%{y:,.0f}원')
        fig_trend.update_layout(template="plotly_white")
        fig_trend.update_yaxes(tickformat=",")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # 엑셀과 비슷한 형태로 표 요약 (가장 최근 기준)
        st.subheader("📋 가장 최근 자산 상세 요약")
        latest_df = asset_df[asset_df['날짜'] == latest_date].copy()
        
        # 보기 편하게 소유자를 열(Column)로, 자산항목을 행(Row)으로 변환
        pivot_df = latest_df.pivot_table(index='자산항목', columns='소유자', values='금액', aggfunc='sum').fillna(0)
        
        # 총계 컬럼 추가
        pivot_df['총계'] = pivot_df.sum(axis=1)
        
        # 원단위 포맷팅하여 표 출력
        st.dataframe(pivot_df.style.format("{:,.0f}원"), use_container_width=True)
