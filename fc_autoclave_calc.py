import pandas as pd

def format_value(value, unit):
    if value is None:
        return ""
    try:
        value = float(value)
    except:
        return str(value)
    if unit in ('%', 'г/т', 'шт'):
        return f"{value:.2f}"
    elif unit == 'т':
        return f"{value:.0f}"
    else:
        return f"{value:.2f}"

def calculate_missing_seq_param(S=None, As=None, Seq=None, k=1.0):
    try:
        if Seq is None and S is not None and As is not None:
            return S + k * As
        elif S is None and Seq is not None and As is not None:
            return Seq - k * As
        elif As is None and Seq is not None and S is not None:
            return (Seq - S) / k
        else:
            return None
    except:
        return None

def calc_fc_autoclave(name_base, Au_base, S_base, As_base, Seq_base,
                      work_hours_year, seq_productivity_per_hour,
                      name_ext, Au_ext, S_ext, As_ext, Seq_ext,
                      As_target, k=1.0, Q_base=None, Q_ext=None,
                      yield_after_cond=100.0, mode=1):
    results = {}

    if Seq_base is None:
        Seq_base = calculate_missing_seq_param(S_base, As_base, None, k)
    if S_base is None:
        S_base = calculate_missing_seq_param(None, As_base, Seq_base, k)
    if As_base is None:
        As_base = calculate_missing_seq_param(S_base, None, Seq_base, k)
    f_Seq_base = Seq_base / 100 if Seq_base else 0.0

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

    seq_prod_per_year = seq_productivity_per_hour * work_hours_year
    total_capacity    = seq_prod_per_year * 2

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

    # ─── РЕЖИМ 3: смешение по объёмам ───
    if mode == 3:
        Qb = Q_base or 0.0
        Qe = Q_ext or 0.0
        mix_q = Qb + Qe
        if mix_q == 0:
            _record_inputs()
            return results

        As_mix    = ((As_base or 0.0) * Qb + (As_ext or 0.0) * Qe) / mix_q
        f_Seq_mix = (f_Seq_base * Qb + f_Seq_ext * Qe) / mix_q
        Seq_mix   = f_Seq_mix * 100

        total_seq_mass = f_Seq_mix * mix_q
        num_autoclaves = total_seq_mass / seq_prod_per_year if seq_prod_per_year else 0.0

        mass_after_yield = mix_q * (yield_after_cond / 100.0)
        Au_total_mass   = (Au_base or 0.0) * Qb + (Au_ext or 0.0) * Qe
        Au_mix          = Au_total_mass / mass_after_yield if mass_after_yield else 0.0
        total_au_mass   = Au_mix * mass_after_yield / 1000.0
        mass_kek_fk     = mass_after_yield

        _record_inputs()
        results.update({
            'Max_Q_base_t':     0,
            'Max_Q_ext_t':      0,
            'Max_total_Q_t':    0,
            'Q_base_t':         Qb,
            'Q_ext_required_t': Qe,
            'Mix_total_Q_t':    mix_q,
            'Mix_As_%':         As_mix,
            'Mix_Seq_%':        Seq_mix,
            'Total_Seq_mass_t': total_seq_mass,
            'Autoclaves_used':  round(num_autoclaves, 2),
            'Mix_Au_g_t':       round(Au_mix, 2),
            'Total_Au_kg':      round(total_au_mass, 0),
            'Mass_kek_fk_t':    mass_kek_fk
        })
        return results

    # ─── РЕЖИМЫ 1 и 2 ───
    if mode == 1:
        # расчёт коэффициента замещения
        coeff = (As_target - As_base) / (As_ext - As_target) if As_ext != As_target else 0.0
        Max_Qb = total_capacity / (f_Seq_base + f_Seq_ext * coeff) if (f_Seq_base + f_Seq_ext * coeff) else 0.0
        Max_Qe = Max_Qb * coeff

        # Расчёт фактических масс:
        if Q_base and not Q_ext:
            Qb = Q_base
            Qe = Qb * coeff
        elif Q_ext and not Q_base:
            Qe = Q_ext
            Qb = Qe / coeff if coeff != 0 else 0
        elif Q_base and Q_ext:
            Qb = Q_base
            Qe = Q_ext
        else:
            Qb = Max_Qb
            Qe = Max_Qe

    else:  # mode == 2
        Max_Qb = total_capacity / f_Seq_base if f_Seq_base else 0.0
        Max_Qe = 0.0

        Qb = Q_base if Q_base is not None else Max_Qb
        Qe = 0.0

    mix_q          = Qb + Qe
    As_mix         = (As_base * Qb + As_ext * Qe) / mix_q if mix_q else 0.0
    f_Seq_mix      = (f_Seq_base * Qb + f_Seq_ext * Qe) / mix_q if mix_q else 0.0
    Seq_mix        = f_Seq_mix * 100
    total_seq_mass = f_Seq_mix * mix_q
    num_autoclaves = total_seq_mass / seq_prod_per_year if seq_prod_per_year else 0.0

    mass_after_yield = mix_q * (yield_after_cond / 100.0)
    Au_total_mass   = (Au_base or 0.0) * Qb + (Au_ext or 0.0) * Qe
    Au_mix          = Au_total_mass / mass_after_yield if mass_after_yield else 0.0
    total_au_mass   = Au_mix * mass_after_yield / 1000.0
    mass_kek_fk     = mass_after_yield

    _record_inputs()
    results.update({
        'Max_Q_base_t':     Max_Qb,
        'Max_Q_ext_t':      Max_Qe,
        'Max_total_Q_t':    Max_Qb + Max_Qe,
        'Q_base_t':         Qb,
        'Q_ext_required_t': Qe,
        'Mix_total_Q_t':    mix_q,
        'Mix_As_%':         As_mix,
        'Mix_Seq_%':        Seq_mix,
        'Total_Seq_mass_t': total_seq_mass,
        'Autoclaves_used':  round(num_autoclaves, 2),
        'Mix_Au_g_t':       round(Au_mix, 2),
        'Total_Au_kg':      round(total_au_mass, 0),
        'Mass_kek_fk_t':    mass_kek_fk
    })

    return results
