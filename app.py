import streamlit as st
import pandas as pd
import random
from streamlit_gsheets import GSheetsConnection
from streamlit_sortables import sort_items

# 페이지 설정
st.set_page_config(page_title="조기축구 라인업 메이커", layout="wide")

# 세부 포지션 정의
POSITIONS = ["LW", "ST", "RW", "CMF", "DMF", "CB", "LB", "RB"]

# --- 구글 시트 DB 로드/저장 함수 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        if df.empty or "이름" not in df.columns:
            return pd.DataFrame(columns=["이름", "1순위포지션", "2순위포지션"])
        return df.dropna(how="all")
    except Exception as e:
        st.error(f"🚨 구글 시트 연결 에러 상세 내용:\n\n{e}")
        st.info("위 에러 메시지를 복사해서 알려주시면 바로 해결해 드리겠습니다!")
        return pd.DataFrame(columns=["이름", "1순위포지션", "2순위포지션"])

def save_db(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
    except Exception as e:
        st.error(f"구글 시트에 저장하는 중 오류가 발생했습니다: {e}")

# 세션 상태에 DB 저장
if 'db' not in st.session_state:
    st.session_state.db = load_db()

# 타이틀 및 설명
st.title("⚽ 4-3-3 조기축구 쿼터별 라인업 자동 생성기")
st.markdown("상단 탭을 이용해 **회원을 먼저 등록**한 뒤, **오늘의 경기**에서 참석자를 선택하세요.")

# UI를 두 개의 탭으로 분리
tab_match, tab_manage = st.tabs(["⚽ 오늘의 경기", "👥 회원 관리 (Google Sheets)"])

# ==========================================
# 탭 2: 회원 관리 (구글 시트 연동)
# ==========================================
with tab_manage:
    st.header("👥 팀원 명부 관리")
    st.write("이곳에서 선수를 등록/수정하면 **내 구글 스프레드시트**에 영구적으로 안전하게 저장됩니다!")
    
    with st.form("new_player_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_name = st.text_input("새 선수 이름 (예: 손흥민)")
        with col2:
            new_pos1 = st.selectbox("1순위 선호 포지션", POSITIONS)
        with col3:
            new_pos2 = st.selectbox("2순위 선호 포지션", POSITIONS)
        
        submit_btn = st.form_submit_button("➕ 선수 등록하기")
        
        if submit_btn and new_name:
            if new_name in st.session_state.db['이름'].values:
                st.error("이미 존재하는 이름입니다. 다른 이름을 사용해주세요.")
            else:
                new_row = pd.DataFrame([{"이름": new_name, "1순위포지션": new_pos1, "2순위포지션": new_pos2}])
                st.session_state.db = pd.concat([st.session_state.db, new_row], ignore_index=True)
                save_db(st.session_state.db)
                st.success(f"'{new_name}' 선수가 구글 시트에 성공적으로 등록되었습니다!")
                st.rerun()
                
    st.divider()
    st.subheader("📋 전체 등록 선수 목록")
    st.caption("표 안에서 직접 포지션을 변경하거나, 왼쪽 체크박스를 선택해 삭제(Del)할 수 있습니다.")
    
    # 💡 에러 픽스: use_container_width=True 대신 width="stretch" 사용
    edited_db = st.data_editor(
        st.session_state.db,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "1순위포지션": st.column_config.SelectboxColumn(options=POSITIONS, required=True),
            "2순위포지션": st.column_config.SelectboxColumn(options=POSITIONS, required=True),
        }
    )
    
    if st.button("💾 목록 변경사항 구글 시트에 덮어쓰기"):
        st.session_state.db = edited_db
        save_db(st.session_state.db)
        st.success("회원 명단이 구글 스프레드시트에 안전하게 동기화되었습니다.")

# ==========================================
# 탭 1: 오늘의 경기 (드래그 앤 드롭 추가)
# ==========================================
with tab_match:
    st.header("🏃‍♂️ 오늘 참석자 선택")
    
    if st.session_state.db.empty:
        st.warning("등록된 선수가 없습니다. 먼저 **[👥 회원 관리]** 탭에서 선수들을 등록해주세요!")
    else:
        all_players = st.session_state.db['이름'].tolist()
        
        # 1단계: 순서 상관없이 일단 다 고르기
        selected_players = st.multiselect(
            "1️⃣ 오늘 참석한 회원들을 모두 골라주세요 (순서 무관):",
            options=all_players
        )
        
        if selected_players:
            st.divider()
            st.subheader("2️⃣ 도착 순서 맞추기 (드래그 앤 드롭 🖱️)")
            st.info("💡 마우스로 이름을 클릭한 채 위아래로 끌어다 놓으세요! (가장 위가 1등, 가장 아래가 지각)")
            
            # 마법의 드래그 앤 드롭 정렬 기능!
            ordered_players = sort_items(selected_players)
            
            st.divider()
            st.subheader("3️⃣ 조기 귀가자 체크")
            st.caption("도착 순서는 위에서 드래그한 대로 자동 부여되었습니다. 일찍 가는 사람의 쿼터 수만 수정해 주세요.")
            
            today_data = []
            for i, name in enumerate(ordered_players):
                player_info = st.session_state.db[st.session_state.db['이름'] == name].iloc[0]
                today_data.append({
                    "이름": name,
                    "1순위": player_info["1순위포지션"],
                    "2순위": player_info["2순위포지션"],
                    "도착순서": i + 1, # 드래그한 순서대로 자동으로 1, 2, 3... 부여됨
                    "참여가능쿼터": 4
                })
            
            today_df = pd.DataFrame(today_data)
            
            # 도착순서는 자동 입력되므로 잠금(disabled) 처리
            # 💡 에러 픽스: use_container_width=True 대신 width="stretch" 사용
            edited_today_df = st.data_editor(
                today_df,
                disabled=["이름", "1순위", "2순위", "도착순서"],
                hide_index=True,
                width="stretch",
                column_config={
                    "참여가능쿼터": st.column_config.NumberColumn(min_value=1, max_value=4, step=1, required=True)
                }
            )
            
            if st.button("🚀 라인업 및 포메이션 짜기", type="primary"):
                df = edited_today_df.copy()
                df['penalty_count'] = 0
                df['last_penalty_q'] = 0
                quarter_results = {}
                
                formation_to = {
                    "LW": 1, "ST": 1, "RW": 1,
                    "CMF": 2, "DMF": 1,
                    "CB": 2, "LB": 1, "RB": 1
                }
                
                for q in range(1, 5):
                    available = df[df['참여가능쿼터'] >= q].copy()
                    if len(available) == 0: continue
                        
                    total_available = len(available)
                    gk_needed = 1 if total_available > 0 else 0
                    field_needed = min(10, max(0, total_available - gk_needed))
                    rest_count = max(0, total_available - (field_needed + gk_needed))
                    penalty_needed = gk_needed + rest_count
                    
                    eligible = available[available['last_penalty_q'] != q - 1].copy()
                    if len(eligible) < penalty_needed:
                        eligible = available.copy()
                        
                    eligible = eligible.sort_values(by=['penalty_count', '도착순서'], ascending=[True, False])
                    penalized_players = eligible.head(penalty_needed)
                    penalized_names = penalized_players['이름'].tolist()
                    
                    if penalized_names:
                        gk_name = random.choice(penalized_names)
                        rest_names = [name for name in penalized_names if name != gk_name]
                    else:
                        gk_name = None
                        rest_names = []
                        
                    df.loc[df['이름'].isin(penalized_names), 'penalty_count'] += 1
                    df.loc[df['이름'].isin(penalized_names), 'last_penalty_q'] = q
                    
                    field_players = available[~available['이름'].isin(penalized_names)].copy()
                    field_players = field_players.sample(frac=1).reset_index(drop=True)
                    
                    assigned = {pos: [] for pos in formation_to.keys()}
                    unassigned = []
                    
                    for idx, row in field_players.iterrows():
                        pos1 = row['1순위']
                        if len(assigned[pos1]) < formation_to[pos1]:
                            assigned[pos1].append(row['이름'])
                            field_players.at[idx, 'assigned'] = True
                        else:
                            field_players.at[idx, 'assigned'] = False
                            
                    for idx, row in field_players[field_players['assigned'] == False].iterrows():
                        pos2 = row['2순위']
                        if len(assigned[pos2]) < formation_to[pos2]:
                            assigned[pos2].append(row['이름'])
                            field_players.at[idx, 'assigned'] = True
                        else:
                            unassigned.append(row['이름'])
                            
                    random.shuffle(unassigned)
                    for pos, max_num in formation_to.items():
                        while len(assigned[pos]) < max_num and unassigned:
                            assigned[pos].append(unassigned.pop(0))
                            
                    quarter_results[q] = {
                        "formation": assigned,
                        "GK": gk_name,
                        "Rest": rest_names
                    }
                    
                st.divider()
                st.subheader("🎯 쿼터별 포메이션 결과")
                
                q_tabs = st.tabs([f"{q}쿼터" for q in quarter_results.keys()])
                for i, (q, res) in enumerate(quarter_results.items()):
                    with q_tabs[i]:
                        f = res["formation"]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown("#### ⚔️ 공격 (FW)")
                            st.write(f"**LW:** {', '.join(f['LW']) if f['LW'] else '-'}")
                            st.write(f"**ST:** {', '.join(f['ST']) if f['ST'] else '-'}")
                            st.write(f"**RW:** {', '.join(f['RW']) if f['RW'] else '-'}")
                        with col2:
                            st.markdown("#### 🛡️ 미드 (MF)")
                            st.write(f"**CMF:** {', '.join(f['CMF']) if f['CMF'] else '-'}")
                            st.write(f"**DMF:** {', '.join(f['DMF']) if f['DMF'] else '-'}")
                        with col3:
                            st.markdown("#### 🧱 수비 (DF)")
                            st.write(f"**CB:** {', '.join(f['CB']) if f['CB'] else '-'}")
                            st.write(f"**LB:** {', '.join(f['LB']) if f['LB'] else '-'}")
                            st.write(f"**RB:** {', '.join(f['RB']) if f['RB'] else '-'}")
                            
                        st.divider()
                        st.info(f"🧤 **키퍼 (GK):** {res['GK'] if res['GK'] else '없음'}")
                        if res['Rest']:
                            st.warning(f"☕ **휴식:** {', '.join(res['Rest'])}")
                            
                st.divider()
                st.subheader("📊 개인별 출전 요약")
                summary_df = df[['이름', '도착순서', '참여가능쿼터', 'penalty_count']].rename(columns={'penalty_count': '키퍼/휴식 횟수'})
                summary_df['실제 필드 뛴 쿼터수'] = summary_df['참여가능쿼터'] - summary_df['키퍼/휴식 횟수']
                
                # 💡 에러 픽스: use_container_width=True 대신 width="stretch" 사용
                st.dataframe(summary_df, width="stretch")