import pandas as pd

# Форматирование значений
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

# Расчёт недостающих параметров Seq ↔︎ S ↔︎ As
# k — поправочный коэффициент из методики ПАО «Полиметалл»

def calculate_missing_seq_param(S, As, Seq, k):
    if Seq is not None:
        return Seq
    if S is not None:
        return S * k
    if As is not None:
        return As * k
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

    # ---➤ Fast exit when As_target is 0 (no arsenic target): use actual volumes to compute blended mix
    if mode == 1 and (As_target is None or As_target == 0):
        # Determine supplied volumes; default to maximal base capacity if not provided
        total_capacity = (seq_productivity_per_hour * work_hours_year) * 2
        if Q_base is None and Q_ext is None:
            Q_base = total_capacity / f_Seq_base if f_Seq_base else 0.0
            Q_ext_required = 0.0
        else:
            Q_base = Q_base or 0.0
            Q_ext_required = Q_ext or 0.0

        mix_total_q = Q_base + Q_ext_required
        if mix_total_q == 0:
            return results  # nothing to calculate

        # Weighted averages for compositions
        As_mix = ((As_base or 0.0) * Q_base + (As_ext or 0.0) * Q_ext_required) / mix_total_q
        f_Seq_mix = (f_Seq_base * Q_base + f_Seq_ext * Q_ext_required) / mix_total_q
        Seq_mix = f_Seq_mix * 100

        # Total Seq mass and autoclaves
        total_seq_mass = f_Seq_mix * mix_total_q
        seq_productivity_per_year = seq_productivity_per_hour * work_hours_year
        num_autoclaves = total_seq_mass / seq_productivity_per_year if seq_productivity_per_year else 0.0

        # Gold
        Au_total_mass = (Au_base or 0.0) * Q_base + (Au_ext or 0.0) * Q_ext_required
        mass_after_yield = mix_total_q * (yield_after_cond / 100)
        Au_mix = Au_total_mass / mass_after_yield if mass_after_yield else 0.0

        # Update results and return
        results.update({
            'Max_Q_base_t': Q_base,
            'Max_Q_ext_t': Q_ext_required,
            'Max_total_Q_t': mix_total_q,
            'Q_base_t': Q_base,
            'Q_ext_required_t': Q_ext_required,
            'Mix_total_Q_t': mix_total_q,
            'Mix_As_%': As_mix,
            'Mix_Seq_%': Seq_mix,
            'Total_Seq_mass_t': total_seq_mass,
            'Autoclaves_used': round(num_autoclaves, 2),
            'Mix_Au_g_t': round(Au_mix, 2),
            'Total_Au_kg': round(Au_total_mass / 1000, 0),
        })
        return results

    results.update({
        'S_base_%': S_base, 'As_base_%': As_base, 'Seq_base_%': Seq_base, 'Au_base': Au_base or 0.0,
        'S_ext_%': S_ext, 'As_ext_%': As_ext, 'Seq_ext_%': Seq_ext, 'Au_ext': Au_ext or 0.0,
        'As_target': As_target, 'k': k, 'yield_after_cond': yield_after_cond
    })

    seq_productivity_per_year = seq_productivity_per_hour * work_hours_year
    total_capacity = seq_productivity_per_year * 2
    results['Total_capacity_t'] = total_capacity

    if mode == 1:
        coeff = (As_target - As_base) / (As_ext - As_target) if As_ext != As_target else 0.0
        Q_base_max = total_capacity / (f_Seq_base + f_Seq_ext * coeff) if (f_Seq_base + f_Seq_ext * coeff) else 0.0
        Q_ext_required_max = Q_base_max * coeff
        max_total_q = Q_base_max + Q_ext_required_max

        if Q_base is not None and Q_ext is None:
            Q_ext_required = Q_base * coeff
        elif Q_ext is not None and Q_base is None:
            Q_base = Q_ext * coeff
            Q_ext_required = Q_ext
        else:
            Q_base = Q_base_max
            Q_ext_required = Q_ext_required_max

        mix_total_q = Q_base + Q_ext_required
        As_mix = (As_base * Q_base + As_ext * Q_ext_required) / mix_total_q if mix_total_q else 0.0
        f_Seq_mix = (f_Seq_base * Q_base + f_Seq_ext * Q_ext_required) / mix_total_q if mix_total_q else 0.0
        Seq_mix = f_Seq_mix * 100
    else:
        Q_base_max = total_capacity / f_Seq_base if f_Seq_base else 0.0
        mix_total_q = Q_base if Q_base else Q_base_max
        As_mix = As_base
        Seq_mix = Seq_base
        f_Seq_mix = f_Seq_base
        Q_ext_required = 0.0
        Q_base = mix_total_q
        max_total_q = Q_base_max

    total_seq_mass = f_Seq_mix * mix_total_q
    num_autoclaves = total_seq_mass / seq_productivity_per_year if seq_productivity_per_year else 0.0

    # ⬇️ Исправление расчёта золота после кондиционирования
    Au_total_mass = (Au_base or 0.0) * Q_base + (Au_ext or 0.0) * Q_ext_required
    mass_after_yield = mix_total_q * (yield_after_cond / 100)
    Au_mix = Au_total_mass / mass_after_yield if mass_after_yield else 0.0
    results['Mix_Au_g_t'] = round(Au_mix, 2)
    return results
