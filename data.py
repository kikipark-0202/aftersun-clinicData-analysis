import pandas as pd
import numpy as np
import re

TYPE_KR = {
    'urology': '비뇨기과',
    'obstetrics': '산부인과',
    'public_health': '보건소',
    'standalone_sti': '성병전문',
    'andrology': '남성의학과',
}


def load_and_process_data(filepath):
    df = pd.read_excel(filepath, sheet_name='Clinic Data', header=1)
    df = df.iloc[1:].reset_index(drop=True)
    df = df[~df['기관명\n(Clinic Name)'].astype(str).str.contains('검사불가|○○', na=False)]
    df = df.reset_index(drop=True)

    df['gender_available'] = 'both'
    df.loc[df['기관명\n(Clinic Name)'].str.contains('포유문', na=False), 'gender_available'] = 'female_only'

    df['gonorrhea_gender'] = 'both'
    for idx, row in df.iterrows():
        sti = str(row['검사 가능\nSTI 종류'])
        if '임질(남자)' in sti or '임질(남성)' in sti:
            df.at[idx, 'gonorrhea_gender'] = 'male_only'

    yn_cols = ['익명검사\n가능 여부', '실명등록\n필수 여부', '별도 대기실\n여부',
               '남성 의사\n여부', '여성 의사\n여부', '보험 적용\n여부',
               '자가키트\n판매 여부', '주말 운영\n여부', '온라인 예약\n가능 여부',
               'PEP\n처방 가능', 'PrEP\n상담 가능', '원내 약국\n여부']
    for col in yn_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x:
                1.0 if x == 'Y' else 0.0 if x == 'N' else
                0.5 if x == 'Only HIV' else
                0.5 if isinstance(x, str) and x not in ['Unknown', 'X', 'N/A', '없음'] and len(x) > 1 else
                None if x in ['Unknown', 'X', 'N/A', '없음'] else
                None if pd.isna(x) else x)

    def parse_price(v):
        if isinstance(v, (int, float)):
            return v if not pd.isna(v) else None
        if not isinstance(v, str):
            return None
        if v.strip() in ['Unknown', 'X', '없음', '']:
            return None
        ps = []
        for m in re.findall(r'(\d+)\s*만\s*원?', v):
            ps.append(int(m) * 10000)
        c = v.replace(',', '')
        for m in re.findall(r'(\d{4,})', c):
            ps.append(int(m))
        if not ps:
            for m in re.findall(r'(\d+)', c):
                ps.append(int(m))
        return min(ps) if ps else None

    df['price_min'] = df['기본 검사\n비용 (원)'].apply(parse_price)
    for name, price in {'맨스톤비뇨의학과 (용산)': 10000, '한스비뇨기과': 20000, '강동연세비뇨기과': 20000}.items():
        df.loc[df['기관명\n(Clinic Name)'].str.contains(name, na=False, regex=False), 'price_min'] = price

    def parse_sti(row):
        v = row['검사 가능\nSTI 수']
        if isinstance(v, (int, float)) and not pd.isna(v):
            return int(v)
        t = str(row['검사 가능\nSTI 종류'])
        if t in ['nan', 'Unknown', 'X', '-']:
            return None
        j = re.findall(r'(\d+)\s*종', t)
        if j:
            return max(int(m) for m in j)
        items = [x.strip() for x in t.split(',') if x.strip() and x.strip() != '-']
        return len(items) if items else None

    df['sti_count_parsed'] = df.apply(parse_sti, axis=1)

    rn = {
        'ID': 'clinic_id', '기관명\n(Clinic Name)': 'clinic_name',
        '지역구\n(District)': 'district', '기관 유형\n(Type)': 'clinic_type',
        '익명검사\n가능 여부': 'anonymous_testing', '실명등록\n필수 여부': 'realname_required',
        '예약 방법\n(Booking)': 'booking_method', '별도 대기실\n여부': 'separate_waiting',
        '결과 확인\n방법': 'results_method', '남성 의사\n여부': 'doctor_male',
        '여성 의사\n여부': 'doctor_female', '기본 검사\n비용 (원)': 'price_raw',
        '보험 적용\n여부': 'insurance_accepted', '자가키트\n판매 여부': 'home_kit_available',
        '주말 운영\n여부': 'weekend_available', '최근접\n지하철역': 'nearest_subway',
        '온라인 예약\n가능 여부': 'online_booking', 'PEP\n처방 가능': 'pep_available',
        'PrEP\n상담 가능': 'prep_consultation', '원내 약국\n여부': 'onsite_pharmacy',
    }
    df = df.rename(columns=rn)
    return df


def compute_subscores(df, gender='all'):
    dfs = df.copy()

    if gender == 'male':
        dfs = dfs[dfs['gender_available'] != 'female_only'].reset_index(drop=True)
    elif gender == 'female':
        dfs = dfs[dfs['gender_available'] != 'male_only'].reset_index(drop=True)

    if gender == 'female':
        dfs['sti_adj'] = dfs.apply(lambda r:
            max(0, r['sti_count_parsed'] - 1)
            if r['gonorrhea_gender'] == 'male_only' and not pd.isna(r['sti_count_parsed'])
            else r['sti_count_parsed'], axis=1)
    else:
        dfs['sti_adj'] = dfs['sti_count_parsed']

    bk = {'online': 1.0, 'online+phone': 0.8, 'phone+walk_in': 0.4, 'walk_in': 0.3, 'phone': 0.5}
    rs = {'app': 1.0, 'app+phone': 0.9, 'online_portal': 0.8, 'mail+online': 0.7,
          'mail': 0.6, 'phone': 0.5, 'in_person': 0.2}
    dfs['booking_score'] = dfs['booking_method'].map(bk)
    dfs['results_score'] = dfs['results_method'].map(rs)

    def norm(s):
        mn, mx = s.min(), s.max()
        return pd.Series(0.5, index=s.index) if mx == mn else (s - mn) / (mx - mn)

    def inv_norm(s):
        mn, mx = s.min(), s.max()
        return pd.Series(0.5, index=s.index) if mx == mn else 1 - (s - mn) / (mx - mn)

    dfs['sti_norm'] = norm(dfs['sti_adj'])
    dfs['price_norm'] = inv_norm(dfs['price_min'])

    score_cols = ['anonymous_testing', 'realname_required', 'separate_waiting',
                  'doctor_male', 'doctor_female', 'insurance_accepted',
                  'pep_available', 'prep_consultation', 'onsite_pharmacy',
                  'booking_score', 'results_score', 'sti_norm', 'price_norm',
                  'weekend_available', 'online_booking', 'home_kit_available']
    for col in score_cols:
        if col in dfs.columns:
            dfs[col] = pd.to_numeric(dfs[col], errors='coerce')
            dfs[col] = dfs[col].fillna(dfs[col].median()).fillna(0.5)

    dfs['realname_inv'] = 1 - dfs['realname_required']
    dfs['s_privacy'] = (dfs['anonymous_testing'] * 0.20 + dfs['realname_inv'] * 0.20 +
                        dfs['booking_score'] * 0.15 + dfs['separate_waiting'] * 0.15 +
                        dfs['results_score'] * 0.15 + dfs['online_booking'] * 0.15)
    dfs['s_clinical'] = (dfs['sti_norm'] * 0.30 + dfs['doctor_male'] * 0.15 +
                         dfs['doctor_female'] * 0.15 + dfs['insurance_accepted'] * 0.20 +
                         dfs['home_kit_available'] * 0.20)
    dfs['s_cost'] = dfs['price_norm']
    dfs['s_access'] = (dfs['weekend_available'] * 0.40 + dfs['online_booking'] * 0.30 +
                       dfs['booking_score'] * 0.30)
    dfs['s_meds'] = (dfs['pep_available'] * 0.40 + dfs['prep_consultation'] * 0.35 +
                     dfs['onsite_pharmacy'] * 0.25)
    dfs['s_trust'] = 0.5

    def sf(v):
        return None if pd.isna(v) else float(v)

    def si(v):
        return None if pd.isna(v) else int(v)

    result = []
    for _, row in dfs.iterrows():
        result.append({
            'name':             str(row['clinic_name']),
            'district':         str(row.get('district', '')),
            'type':             str(row.get('clinic_type', '')),
            'type_kr':          TYPE_KR.get(str(row.get('clinic_type', '')), str(row.get('clinic_type', ''))),
            'subway':           str(row.get('nearest_subway', '')),
            'price':            si(row['price_min']),
            'sti_count':        si(row['sti_adj']),
            'gender_available': str(row.get('gender_available', 'both')),
            's_privacy':        round(float(row['s_privacy']), 4),
            's_clinical':       round(float(row['s_clinical']), 4),
            's_cost':           round(float(row['s_cost']), 4),
            's_access':         round(float(row['s_access']), 4),
            's_meds':           round(float(row['s_meds']), 4),
            's_trust':          round(float(row['s_trust']), 4),
            'pep_available':    sf(row.get('pep_available')),
            'anonymous_testing':  sf(row.get('anonymous_testing')),
            'realname_required':  sf(row.get('realname_required')),
            'booking_method':     str(row.get('booking_method', '')),
            'results_method':     str(row.get('results_method', '')),
            'weekend_available':  sf(row.get('weekend_available')),
            'prep_consultation':  sf(row.get('prep_consultation')),
        })
    return result
