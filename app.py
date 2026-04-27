# (전체 코드는 동일하며 저장 버튼 부분의 로직을 더 명확히 보강했습니다)

            # 상세 장부 수정 섹션 내 저장 버튼 로직
            if st.button("💾 변경사항 저장"):
                with st.spinner("데이터를 파일에 기록 중입니다..."):
                    # 1. 현재 선택된 달 이외의 데이터 가져오기
                    other_months = df_a[df_a['연월'] != sel_m]
                    # 2. 수정한 데이터와 합치기
                    final_df = pd.concat([other_months, edited_df], ignore_index=True)
                    # 3. 날짜순 정렬 및 불필요한 컬럼 제거
                    if '연월' in final_df.columns:
                        final_df = final_df.drop(columns=['연월'])
                    final_df = final_df.sort_values(by='날짜', ascending=False).reset_index(drop=True)
                    # 4. CSV 파일에 실제 저장 (이 시점에 파일이 업데이트됩니다)
                    final_df.to_csv(data_file, index=False, encoding='utf-8-sig')
                    
                st.success(f"{sel_m} 데이터가 안전하게 저장되었습니다!")
                st.rerun()
