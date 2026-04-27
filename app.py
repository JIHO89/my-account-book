# --- 3. 구글 시트 연결 및 데이터 로드 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # [보완] 주소를 명시적으로 다시 한번 참조하여 읽기 경로를 확실히 합니다.
        # 만약 secrets 설정이 완벽하다면 주소 없이 conn.read(ttl=0)만 해도 됩니다.
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1S4WUWBYV3bgi-Z7YA1wY3RXaRvY0w_8PEyOdkCxbiQo",
            ttl=0
        )
        # ... 이하 생략
