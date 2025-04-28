import pandas as pd

# Форматирование значений (для Streamlit)
def format_value(value, unit):
    if value is None:
        return ""
    try:
        value = float(value)
    except:
        return str(value)
    if unit in ('%', 'г/т', 'шт'):
        return f"{value:.2f}"
    elif unit in ('т', 'кг'):
        return f"{value:.0f}"
    else:
        return f"{value:.2f}"

# Вычисление недостающего Seq по S или As
def calculate_missing_seq_param(S, As, Seq, k):
    if Seq is not None:
        return Seq
    if S is not None:
        return S * k
    if As is not None:
        return As * k
    return None

def calc_fc_autoclave(
    name_base, Au_base, S_base, As_base, Seq_base,
    work_hours_year, seq_productivity_per_hour,
    name_ext, Au_ext, S_ext, As_ext, Seq_ext,
    As_target, k=1.0, Q_base=None, Q_ext=None,
    yield_after_cond=100.0, mode=1
):
    results = {}

    # 1) Подготовка базового концентрата
    if Seq_base is None:
        Seq_base = calculate_missing_seq_param(S_base, As_base, None, k)
    if S_base is None:
        S_base = calculate_missing_seq_param(None, As_base, Seq_base, k)
    if As_base is None:
        As_base = calculate_missing_seq_param(S_base, None, Seq_base, k)
    f_Seq_base = Seq_base / 100 if Seq_base else 0.0

    # 2) Подготовка стороннего, только для режима 1
    if mode == 1:
        if Seq_ext is None:
            Seq_ext = calculate_missing_seq_param(S_ext, As_ext, None, k)
        if S_ext is None:
            S_ext = calculate_missing_seq_param(None, As_ext, Seq_ext, k)
        if As_ext is None:
            As_ext = calculate_missing_seq_param(S_ext, None, Seq_ext, k)
        f_Seq_ext = Seq_ext / 100 if Seq_ext else 0.0
    else:
        f_Seq_ext = 0.0

    # 3) Общая мощность
    seq_per_year = seq_productivity_per_hour * work_hours_year
    total_capacity = seq_per_year * 2

    # Вспомогательная функция — записать входные параметры
    def _record_inputs():
        results.update({
            'S_base_%':         S_base,
            'As_base_%':        As_base,
            'Seq_base_%':       Seq_base,
            'Au_base':          Au_base or 0.0,
            'S_ext_%':          S_ext,
            'As_ext_%':         As_ext,
            'Seq_ext_%':        Seq_ext,
            'Au_ext':           Au_ext or 0.0,
            'As_target':        As_target,
            'k':                k,
            'yield_after_cond': yield_after_cond,
            'Total_capacity_t': total_capacity,
        })

    # ─── РЕЖИМ 3: СМЕШЕНИЕ ПО ВВЕДЁННЫМ ОБЪЁМАМ ────────────────
    if mode == 3:
        # берём введённые объёмы (None → 0)
        Qb = Q_base or 0.0
        Qe = Q_ext  or 0.0
        mix_q = Qb + Qe
        if mix_q == 0:
            _record_inputs()
            return results

        # Взвешенные средние по составам
        As_mix    = ((As_base or 0.0) * Qb + (As_ext or 0.0) * Qe) / mix_q
        f_Seq_mix = (f_Seq_base * Qb + f_Seq_ext * Qe) / mix_q
        Seq_mix   = f_Seq_mix * 100

        # Масса Seq и автоклавы
        total_seq_mass = f_Seq_mix * mix_q
        num_autoclaves = total_seq_mass / seq_per_year if seq_per_year else 0.0

        # Золото и масса после кондиционирования
        mass_after_yield = mix_q * (yield_after_cond / 100)
        Au_total_mass   = (Au_base or 0.0) * Qb + (Au_ext or 0.0) * Qe
        Au_mix          = Au_total_mass / mass_after_yield if mass_after_yield else 0.0
        mass_kek_fk     = mass_after_yield

        # Записываем и возвращаем
        _record_inputs()
        results.update({
            'Max_Q_base_t':      Qb,
            'Max_Q_ext_t':       Qe,
            'Max_total_Q_t':     mix_q,
            'Q_base_t':          Qb,
            'Q_ext_required_t':  Qe,
            'Mix_total_Q_t':     mix_q,
            'Mix_As_%':          As_mix,
            'Mix_Seq_%':         Seq_mix,
            'Total_Seq_mass_t':  total_seq_mass,
            'Autoclaves_used':   round(num_autoclaves, 2),
            'Mix_Au_g_t':        round(Au_mix, 2),
            'Total_Au_kg':       round(Au_total_mass / 1000, 0),
            'Mass_kek_fk_t':     mass_kek_fk,
        })
        return results

    # ─── РЕЖИМ 1: ДВА КОНЦЕНТРАТА ───────────────────────────────
    if mode == 1:
        coeff = (As_target - As_base) / (As_ext - As_target) if As_ext != As_target else 0.0
        Qb_max = total_capacity / (f_Seq_base + f_Seq_ext * coeff) if (f_Seq_base + f_Seq_ext * coeff) else 0.0
        Qe_max = Qb_max * coeff

        if Q_base is not None and Q_ext is None:
            Qb = Q_base
            Qe = Q_base * coeff
        elif Q_ext is not None and Q_base is None:
            Qe = Q_ext
            Qb = Q_ext * coeff
        else:
            Qb = Qb_max
            Qe = Qe_max

    # ─── РЕЖИМ 2: ОДИН КОНЦЕНТРАТ ──────────────────────────────
    else:  # mode == 2
        Qb = Q_base or (total_capacity / f_Seq_base if f_Seq_base else 0.0)
        Qe = 0.0
        Qb_max = total_capacity / f_Seq_base if f_Seq_base else 0.0
        Qe_max = 0.0

    # Общие расчёты для режимов 1 и 2
    mix_q = Qb + Qe
    As_mix    = (As_base * Qb + As_ext * Qe) / mix_q if mix_q else 0.0
    f_Seq_mix = (f_Seq_base * Qb + f_Seq_ext * Qe) / mix_q if mix_q else 0.0
    Seq_mix   = f_Seq_mix * 100
    total_seq_mass = f_Seq_mix * mix_q
    num_autoclaves  = total_seq_mass / seq_per_year if seq_per_year else 0.0
    mass_after_yield = mix_q * (yield_after_cond / 100)
    Au_total_mass   = (Au_base or 0.0) * Qb + (Au_ext or 0.0) * Qe
    Au_mix          = Au_total_mass / mass_after_yield if mass_after_yield else 0.0
    mass_kek_fk     = mass_after_yield

    _record_inputs()
    results.update({
        'Max_Q_base_t':      Qb,
        'Max_Q_ext_t':       Qe if mode == 1 else 0.0,
        'Max_total_Q_t':     (Qb_max + Qe_max) if mode == 1 else Qb_max,
        'Q_base_t':          Qb,
        'Q_ext_required_t':  Qe if mode == 1 else 0.0,
        'Mix_total_Q_t':     mix_q,
        'Mix_As_%':          As_mix,
        'Mix_Seq_%':         Seq_mix,
        'Total_Seq_mass_t':  total_seq_mass,
        'Autoclaves_used':   round(num_autoclaves, 2),
        'Mix_Au_g_t':        round(Au_mix, 2),
        'Total_Au_kg':       round(Au_total_mass / 1000, 0),
        'Mass_kek_fk_t':     mass_kek_fk,
    })
    return results
