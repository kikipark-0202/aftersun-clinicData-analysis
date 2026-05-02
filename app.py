import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config( 
    page_title="aftersun Privacy Scorecard",
    page_icon="🌞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');            

html, body, [class*="css"] {
    font-family: 'Pretendard', sans-serif;
}
.main-header {
    font-size: 2rem;
    font-weight: 700;
    color: #D97757;
    margin-bottom: 0;
}
.sub-header {
    font-size: 1rem;
    color: #A09E9C;
    margin-top: 0;
}
.metric-card {
    background: #F6F5F3;
    border-radius: 8px;
    padding: 1.2rem;
    text-align: center;
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #F5B338;
}
.metric-label {
    font-size: 0.85rem;
    color: #65615F;
}
.clinic-card {
    border: 1px solid #E1E0DE;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: all 0.2s;
}
.clinic-card:hover {
    border-color: #BFBDBB;
    box-shadow: 0 2px 8px rgba(15,110,86,0.1);
}
.rank-badge {
    display: inline-block;
    background: #BFBDBB;
    color: white;
    border-radius: 40%;
    width: 28px;
    height: 28px;
    line-height: 28px;
    text-align: center;
    font-weight: 700;
    font-size: 0.85rem;
}
.score-bar {
    height: 6px;
    border-radius: 3px;
    background: #EFEEEC;
}
.score-fill {
    height: 6px;
    border-radius: 3px;
    background: #D97757;
}
.tag {
    display: inline-block;
    white-space: nowrap;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    margin-right: 4px;
}
.tag-privacy { background: #F6F5F3; color: #FACC72; }
.tag-clinical { background: #F6F5F3; color: #A5B6C8; }
.tag-cost { background: #F6F5F3; color: #90B4A3; }
.tag-access { background: #F6F5F3; color: #E9B4A8; }
.tag-meds { background: #F6F5F3; color: #A5A2D4; }
.gender-info {
    background: #E0E5EB;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-size: 0.85rem;
    color: #3E5160;
    margin-bottom: 1rem;
}
div[data-testid="stSidebar"] {
    background: #FFF9EC;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA LOADING & PROCESSING
# ============================================================
@st.cache_data
def load_and_process_data(filepath):
    df = pd.read_excel(filepath, sheet_name='Clinic Data', header=1)
    df = df.iloc[1:].reset_index(drop=True)
    df = df[~df['기관명\n(Clinic Name)'].astype(str).str.contains('검사불가|○○', na=False)]
    df = df.reset_index(drop=True)

    # Gender availability
    df['gender_available'] = 'both'
    df.loc[df['기관명\n(Clinic Name)'].str.contains('포유문', na=False), 'gender_available'] = 'female_only'

    df['gonorrhea_gender'] = 'both'
    for idx, row in df.iterrows():
        sti = str(row['검사 가능\nSTI 종류'])
        if '임질(남자)' in sti or '임질(남성)' in sti:
            df.at[idx, 'gonorrhea_gender'] = 'male_only'

    # Y/N standardize
    yn_cols = ['익명검사\n가능 여부','실명등록\n필수 여부','별도 대기실\n여부',
               '남성 의사\n여부','여성 의사\n여부','보험 적용\n여부',
               '자가키트\n판매 여부','주말 운영\n여부','온라인 예약\n가능 여부',
               'PEP\n처방 가능','PrEP\n상담 가능','원내 약국\n여부']
    for col in yn_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x:
                1.0 if x=='Y' else 0.0 if x=='N' else
                0.5 if x=='Only HIV' else
                0.5 if isinstance(x,str) and x not in ['Unknown','X','N/A','없음'] and len(x)>1 else
                None if x in ['Unknown','X','N/A','없음'] else None if pd.isna(x) else x)

    # Price parsing
    def parse_price(v):
        if isinstance(v,(int,float)): return v if not pd.isna(v) else None
        if not isinstance(v,str): return None
        if v.strip() in ['Unknown','X','없음','']: return None
        ps = []
        for m in re.findall(r'(\d+)\s*만\s*원?',v): ps.append(int(m)*10000)
        c = v.replace(',','')
        for m in re.findall(r'(\d{4,})',c): ps.append(int(m))
        if not ps:
            for m in re.findall(r'(\d+)',c): ps.append(int(m))
        return min(ps) if ps else None

    df['price_min'] = df['기본 검사\n비용 (원)'].apply(parse_price)
    for name, price in {'맨스톤비뇨의학과 (용산)':10000,'한스비뇨기과':20000,'강동연세비뇨기과':20000}.items():
        df.loc[df['기관명\n(Clinic Name)'].str.contains(name, na=False), 'price_min'] = price

    # STI count
    def parse_sti(row):
        v = row['검사 가능\nSTI 수']
        if isinstance(v,(int,float)) and not pd.isna(v): return int(v)
        t = str(row['검사 가능\nSTI 종류'])
        if t in ['nan','Unknown','X','-']: return None
        j = re.findall(r'(\d+)\s*종', t)
        if j: return max(int(m) for m in j)
        items = [x.strip() for x in t.split(',') if x.strip() and x.strip()!='-']
        return len(items) if items else None
    df['sti_count_parsed'] = df.apply(parse_sti, axis=1)

    # Rename
    rn = {'ID':'clinic_id','기관명\n(Clinic Name)':'clinic_name',
          '지역구\n(District)':'district','기관 유형\n(Type)':'clinic_type',
          '익명검사\n가능 여부':'anonymous_testing','실명등록\n필수 여부':'realname_required',
          '예약 방법\n(Booking)':'booking_method','별도 대기실\n여부':'separate_waiting',
          '결과 확인\n방법':'results_method','프라이버시\n특이사항':'privacy_notes',
          '검사 가능\nSTI 종류':'sti_types_raw','검사 가능\nSTI 수':'sti_count_raw',
          '남성 의사\n여부':'doctor_male','여성 의사\n여부':'doctor_female',
          '결과 확인 \n소요 시간':'turnaround_time_raw','기본 검사\n비용 (원)':'price_raw',
          '보험 적용\n여부':'insurance_accepted','자가키트\n판매 여부':'home_kit_available',
          '자가키트\n가격 (원)':'home_kit_price_raw','운영 시간':'operating_hours',
          '주말 운영\n여부':'weekend_available','최근접\n지하철역':'nearest_subway',
          '온라인 예약\n가능 여부':'online_booking','PEP\n처방 가능':'pep_available',
          'PrEP\n상담 가능':'prep_consultation','원내 약국\n여부':'onsite_pharmacy',
          '데이터\n출처':'data_source','최종 확인일':'last_verified'}
    df = df.rename(columns=rn)
    return df

def score_clinics(df, user_gender, weights):
    dfs = df.copy()

    # Gender filter
    if user_gender == 'male':
        dfs = dfs[dfs['gender_available'] != 'female_only'].reset_index(drop=True)
    elif user_gender == 'female':
        dfs = dfs[dfs['gender_available'] != 'male_only'].reset_index(drop=True)

    # STI count adjustment
    if user_gender == 'female':
        dfs['sti_adj'] = dfs.apply(lambda r:
            max(0, r['sti_count_parsed']-1) if r['gonorrhea_gender']=='male_only' and not pd.isna(r['sti_count_parsed'])
            else r['sti_count_parsed'], axis=1)
    else:
        dfs['sti_adj'] = dfs['sti_count_parsed']

    # Categorical
    bk = {'online':1.0,'online+phone':0.8,'phone+walk_in':0.4,'walk_in':0.3,'phone':0.5}
    rs = {'app':1.0,'app+phone':0.9,'online_portal':0.8,'mail+online':0.7,'mail':0.6,'phone':0.5,'in_person':0.2}
    dfs['booking_score'] = dfs['booking_method'].map(bk)
    dfs['results_score'] = dfs['results_method'].map(rs)

    # Normalize
    def norm(s):
        mn,mx = s.min(),s.max()
        return pd.Series(0.5,index=s.index) if mx==mn else (s-mn)/(mx-mn)
    def inv_norm(s):
        mn,mx = s.min(),s.max()
        return pd.Series(0.5,index=s.index) if mx==mn else 1-(s-mn)/(mx-mn)

    dfs['sti_norm'] = norm(dfs['sti_adj'])
    dfs['price_norm'] = inv_norm(dfs['price_min'])

    # Fill missing
    sc = ['anonymous_testing','realname_required','separate_waiting',
          'doctor_male','doctor_female','insurance_accepted',
          'pep_available','prep_consultation','onsite_pharmacy',
          'booking_score','results_score','sti_norm','price_norm',
          'weekend_available','online_booking','home_kit_available']
    for col in sc:
        if col in dfs.columns:
            dfs[col] = pd.to_numeric(dfs[col], errors='coerce')
            dfs[col] = dfs[col].fillna(dfs[col].median())
            dfs[col] = dfs[col].fillna(0.5)

    # Category scores
    dfs['realname_inv'] = 1 - dfs['realname_required']
    dfs['s_privacy'] = (dfs['anonymous_testing']*0.20 + dfs['realname_inv']*0.20 +
                        dfs['booking_score']*0.15 + dfs['separate_waiting']*0.15 +
                        dfs['results_score']*0.15 + dfs['online_booking']*0.15)
    dfs['s_clinical'] = (dfs['sti_norm']*0.30 + dfs['doctor_male']*0.15 +
                         dfs['doctor_female']*0.15 + dfs['insurance_accepted']*0.20 +
                         dfs['home_kit_available']*0.20)
    dfs['s_cost'] = dfs['price_norm']
    dfs['s_access'] = (dfs['weekend_available']*0.40 + dfs['online_booking']*0.30 +
                       dfs['booking_score']*0.30)
    dfs['s_meds'] = (dfs['pep_available']*0.40 + dfs['prep_consultation']*0.35 +
                     dfs['onsite_pharmacy']*0.25)
    dfs['s_trust'] = 0.5

    # Weighted composite
    w = weights
    total_w = sum(w.values())
    dfs['composite'] = (
        dfs['s_privacy'] * (w['privacy']/total_w) +
        dfs['s_clinical'] * (w['clinical']/total_w) +
        dfs['s_cost'] * (w['cost']/total_w) +
        dfs['s_access'] * (w['access']/total_w) +
        dfs['s_meds'] * (w['meds']/total_w) +
        dfs['s_trust'] * (w['trust']/total_w)
    )

    return dfs.sort_values('composite', ascending=False).reset_index(drop=True)

# ============================================================
# LOAD DATA
# ============================================================
try:
    df = load_and_process_data('/mnt/user-data/uploads/aftersun_Clinic_Data_Template.xlsx')
except:
    df = load_and_process_data('aftersun_Clinic_Data_Template.xlsx')

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🌞 aftersun")
    st.markdown("**Privacy Scorecard v.1**")
    st.markdown("현재 계속 업데이트 중인 Beta 버전입니다!")
    st.markdown("---")

    st.markdown("### 사용자 설정")
    gender = st.radio(
        "성별",
        options=['all', 'male', 'female'],
        format_func=lambda x: {'all':'전체','male':'남성','female':'여성'}[x],
        index=0,
        horizontal=True
    )

    if gender == 'male':
        st.markdown('<div class="gender-info">🙋🏻‍♂️ 여성전용 기관이 제외됩니다</div>', unsafe_allow_html=True)
    elif gender == 'female':
        st.markdown('<div class="gender-info">🙋🏽‍♀️임질(남성전용) 검사 제한이 반영됩니다</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 가중치 조절")
    st.caption("슬라이더를 움직여 값을 조절하세요")

    w_privacy = st.slider("🔒 프라이버시", 0, 100, 30, 5)
    w_clinical = st.slider("🏥 임상 역량", 0, 100, 25, 5)
    w_cost = st.slider("💰 검사 비용", 0, 100, 15, 5)
    w_access = st.slider("🚇 거리 접근성", 0, 100, 10, 5)
    w_meds = st.slider("💊 약물 처방", 0, 100, 10, 5)
    w_trust = st.slider("⭐ 신뢰도", 0, 100, 10, 5)

    weights = {
        'privacy': w_privacy, 'clinical': w_clinical,
        'cost': w_cost, 'access': w_access,
        'meds': w_meds, 'trust': w_trust
    }

    total = sum(weights.values())
    st.caption(f"**현재 비율:** 프라이버시 {w_privacy/total*100:.0f}% · 임상 {w_clinical/total*100:.0f}% · 비용 {w_cost/total*100:.0f}% · 접근성 {w_access/total*100:.0f}% · 약물 {w_meds/total*100:.0f}% · 신뢰 {w_trust/total*100:.0f}%")

    st.markdown("---")
    st.caption("Data: 18 clinics & public health cares in Seoul · User Survey: N=374")
    st.caption("© 2026 aftersun+ by Kihyun Louis Park")

# ============================================================
# SCORING
# ============================================================
ranked = score_clinics(df, gender, weights)

# ============================================================
# MAIN CONTENT
# ============================================================
st.markdown('<p class="main-header">Aftersun Privacy Scorecard</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">프라이버시, 가격 등 당신의 우선순위에 맞는 성병검사 기관을 찾아보세요</p>', unsafe_allow_html=True)
st.markdown("")

# Metric cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{len(ranked)}</div><div class="metric-label">검사 가능 기관</div></div>', unsafe_allow_html=True)
with c2:
    avg_priv = ranked['s_privacy'].mean()
    st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_priv:.2f}</div><div class="metric-label">평균 프라이버시 점수</div></div>', unsafe_allow_html=True)
with c3:
    free_count = (ranked['price_min'] == 0).sum()
    st.markdown(f'<div class="metric-card"><div class="metric-value">{free_count}</div><div class="metric-label">무료 검사 기관</div></div>', unsafe_allow_html=True)
with c4:
    pep_count = (ranked['pep_available'] == 1.0).sum()
    st.markdown(f'<div class="metric-card"><div class="metric-value">{pep_count}</div><div class="metric-label">PEP 처방 가능</div></div>', unsafe_allow_html=True)

st.markdown("")

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3 = st.tabs(["전체 랭킹", "기관 비교", "전체 분석"])

# --- TAB 1: RANKING ---
with tab1:
    for rank, (_, row) in enumerate(ranked.iterrows(), 1):
        score_pct = row['composite'] * 100
        price_display = f"{int(row['price_min']):,}원" if not pd.isna(row['price_min']) else "정보 없음"
        if row['price_min'] == 0:
            price_display = "무료"

        type_kr = {'urology':'비뇨기과','obstetrics':'산부인과',
                   'public_health':'보건소','standalone_sti':'성병전문',
                   'andrology':'남성의학과'}.get(row['clinic_type'], row['clinic_type'])

        # Gender badge
        gender_badge = ""
        if row['gender_available'] == 'female_only':
            gender_badge = "여성전용"

        col_rank, col_info, col_scores = st.columns([0.8, 4, 5])

        with col_rank:
            if rank <= 3:
                medal = {1:'🥇', 2:'🥈', 3:'🥉'}[rank]
                st.markdown(f"<div style='font-size:2rem;text-align:center;margin-top:10px'>{medal}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center;margin-top:15px'><span class='rank-badge'>{rank}</span></div>", unsafe_allow_html=True)

        with col_info:
            st.markdown(f"**{row['clinic_name']}**{gender_badge}")
            st.caption(f"{type_kr} · {row['district']} · {row.get('nearest_subway','')}")
            st.caption(f"₩{price_display} · STI {int(row.get('sti_adj', row.get('sti_count_parsed',0))) if not pd.isna(row.get('sti_adj', row.get('sti_count_parsed',0))) else '?'}종")

        with col_scores:
            # Score bars
            categories = [
                ('프라이버시', row['s_privacy'], '#FACC72'),
                ('임상', row['s_clinical'], '#A5B6C8'),
                ('비용', row['s_cost'], '#90B4A3'),
                ('접근성', row['s_access'], '#E9B4A8'),
                ('약물', row['s_meds'], '#A5A2D4'),
            ]
            bar_html = f"<div style='margin-top:8px'><strong style='color:#5C3E02;font-size:1.2rem'>{score_pct:.1f}</strong><span style='color:#888;font-size:0.85rem'>/100</span></div>"
            for cat_name, cat_score, cat_color in categories:
                w_px = max(2, cat_score * 100)
                bar_html += f"""<div style='display:flex;align-items:center;gap:6px;margin:2px 0'>
                    <span style='font-size:0.7rem;color:#888;min-width:58px;white-space:nowrap;flex-shrink:0;text-align:right'>{cat_name}</span>
                    <div style='flex:1;height:5px;background:#F1EFE8;border-radius:3px'>
                        <div style='width:{w_px}%;height:5px;background:{cat_color};border-radius:3px'></div>
                    </div>
                    <span style='font-size:0.7rem;color:#888;width:28px'>{cat_score:.2f}</span>
                </div>"""
            st.markdown(bar_html, unsafe_allow_html=True)

        st.markdown("---")

# --- TAB 2: COMPARISON ---
with tab2:
    st.markdown("### 검사 기관 비교")
    st.caption("최대 3개 기관을 선택하여 비교하세요")

    clinic_names = ranked['clinic_name'].tolist()
    selected = st.multiselect("기관 선택", clinic_names,
                               default=clinic_names[:3] if len(clinic_names) >= 3 else clinic_names,
                               max_selections=3)

    if selected:
        selected_df = ranked[ranked['clinic_name'].isin(selected)]

        # Radar chart
        categories_radar = ['프라이버시', '임상 역량', '비용', '접근성', '약물', '신뢰도']
        colors = ['#F5B338', '#8FA5B8', '#D97757']

        fig = go.Figure()
        for idx, (_, row) in enumerate(selected_df.iterrows()):
            values = [row['s_privacy'], row['s_clinical'], row['s_cost'],
                     row['s_access'], row['s_meds'], row['s_trust']]
            values.append(values[0])  # close the polygon
            cats = categories_radar + [categories_radar[0]]

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=cats,
                fill='toself',
                name=row['clinic_name'][:15],
                line_color=colors[idx % len(colors)],
                opacity=0.7
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1], showticklabels=False)),
            showlegend=True,
            height=450,
            margin=dict(l=60, r=60, t=40, b=40),
            font=dict(family="Pretendard", size=12),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detail comparison table
        compare_cols = {
            '기관 유형': 'clinic_type',
            '지역구': 'district',
            '최소 검사비': 'price_min',
            'STI 검사 종류 수': 'sti_adj',
            '익명검사': 'anonymous_testing',
            '실명등록 필수': 'realname_required',
            '예약 방법': 'booking_method',
            '결과 확인': 'results_method',
            '주말 운영': 'weekend_available',
            'PEP 가능': 'pep_available',
            'PrEP 상담': 'prep_consultation',
        }

        compare_data = {}
        for _, row in selected_df.iterrows():
            name = row['clinic_name'][:15]
            vals = {}
            for kr_name, col in compare_cols.items():
                v = row.get(col, 'N/A')
                if isinstance(v, float):
                    if v == 1.0: v = '✅'
                    elif v == 0.0: v = '❌'
                    elif v == 0.5: v = '⚠️ HIV만 가능'
                    elif col == 'price_min': v = f"{int(v):,}원" if v > 0 else "무료"
                    elif col == 'sti_adj': v = f"{int(v)}종"
                    else: v = f"{v:.1f}"
                vals[kr_name] = v
            compare_data[name] = vals

        compare_df = pd.DataFrame(compare_data)
        st.dataframe(compare_df, use_container_width=True, height=440)

# --- TAB 3: ANALYSIS ---
with tab3:
    st.markdown("### 데이터 분석")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 기관 유형별 평균 점수")
        type_avg = ranked.groupby('clinic_type')[['s_privacy','s_clinical','s_cost','s_access','s_meds']].mean()
        type_kr_map = {'urology':'비뇨기과','obstetrics':'산부인과','public_health':'보건소','standalone_sti':'성병전문'}
        type_avg.index = type_avg.index.map(lambda x: type_kr_map.get(x, x))
        type_avg.columns = ['프라이버시','임상','비용','접근성','약물']

        fig2 = go.Figure()
        colors_bar = ['#FACC72','#A5B6C8','#90B4A3','#E9B4A8','#A5A2D4']
        for i, col in enumerate(type_avg.columns):
            fig2.add_trace(go.Bar(
                name=col,
                x=type_avg.index,
                y=type_avg[col],
                marker_color=colors_bar[i],
                opacity=0.85
            ))
        fig2.update_layout(
            barmode='group', height=350,
            margin=dict(l=40,r=20,t=20,b=40),
            font=dict(family="Pretendard", size=11),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            yaxis=dict(range=[0,1])
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.markdown("#### 프라이버시 vs 비용 트레이드오프")
        fig3 = go.Figure()
        type_colors = {'urology':'#FACC72','obstetrics':'#A5B6C8','public_health':'#90B4A3','standalone_sti':'#E9B4A8'}
        for _, row in ranked.iterrows():
            color = type_colors.get(row['clinic_type'], '#888')
            fig3.add_trace(go.Scatter(
                x=[row['s_cost']],
                y=[row['s_privacy']],
                mode='markers+text',
                text=[row['clinic_name'][:8]],
                textposition='top center',
                textfont=dict(size=9),
                marker=dict(size=12, color=color, opacity=0.8),
                showlegend=False,
                hovertext=f"{row['clinic_name']}<br>Composite: {row['composite']:.3f}"
            ))
        fig3.update_layout(
            xaxis_title="비용 점수 (높을수록 저렴)",
            yaxis_title="프라이버시 점수",
            height=350,
            margin=dict(l=40,r=20,t=20,b=60),
            font=dict(family="Pretendard", size=11),
            xaxis=dict(range=[-0.05,1.1]),
            yaxis=dict(range=[-0.05,1.1])
        )
        # Quadrant labels
        fig3.add_annotation(x=0.9, y=0.95, text="저렴 + 안전", showarrow=False,
                           font=dict(size=10, color="#5C3E02"), opacity=0.8)
        fig3.add_annotation(x=0.1, y=0.95, text="비쌈 + 안전", showarrow=False,
                           font=dict(size=10, color="#5C3E02"), opacity=0.8)
        fig3.add_annotation(x=0.9, y=0.05, text="저렴 + 노출", showarrow=False,
                           font=dict(size=10, color="#5C3E02"), opacity=0.8)
        fig3.add_annotation(x=0.1, y=0.05, text="비쌈 + 노출", showarrow=False,
                           font=dict(size=10, color="#5C3E02"), opacity=0.8)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 주요 인사이트")
    
    top_privacy = ranked.nlargest(1, 's_privacy').iloc[0]
    top_cost = ranked.nlargest(1, 's_cost').iloc[0]
    top_clinical = ranked.nlargest(1, 's_clinical').iloc[0]
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        st.markdown(f"**🔒 프라이버시 1위**")
        st.markdown(f"{top_privacy['clinic_name']}")
        st.caption(f"점수: {top_privacy['s_privacy']:.2f}")
    with ic2:
        st.markdown(f"**💰 비용 효율 1위**")
        st.markdown(f"{top_cost['clinic_name']}")
        st.caption(f"점수: {top_cost['s_cost']:.2f}")
    with ic3:
        st.markdown(f"**🏥 임상 역량 1위**")
        st.markdown(f"{top_clinical['clinic_name']}")
        st.caption(f"점수: {top_clinical['s_clinical']:.2f}")

    st.markdown("")
    st.markdown("""
<div style='background:#FFF9EC;border-left:4px solid #F5B338;padding:0.8rem 1rem;border-radius:4px;margin:0.4rem 0;color:#5C3E02'>
💸 <strong>프라이버시-비용 트레이드오프</strong>: 보건소는 무료이지만 프라이버시 점수가 낮고, 사설 클리닉은 비용이 높지만 익명성이 보장됩니다.
</div>
<div style='background:#FFF9EC;border-left:4px solid #F5B338;padding:0.8rem 1rem;border-radius:4px;margin:0.4rem 0;color:#5C3E02'>
💊 <strong>약물 접근성 현실</strong>: 18개 기관 중 PEP 처방이 가능한 곳은 극소수입니다. PEP는 노출 후 72시간 내 복용해야 하기에 해당 정보의 접근성은 특히 중요합니다.
</div>
""", unsafe_allow_html=True)
