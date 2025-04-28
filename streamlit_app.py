import streamlit as st
import pandas as pd
from fc_autoclave_calc import calc_fc_autoclave, calculate_missing_seq_param

st.set_page_config(page_title="Автоклавный расчёт", layout="wide")

# Подписи для таблицы
LABELS = {
    "S_base_%":       "Сера в осн. (%)",
    "As_base_%":      "Мышьяк в осн. (%)",
    "Seq_base_%":     "Серный эквивалент осн. (%)",
    "Au_base":        "Золото в осн. (г/т)",
    "S_ext_%":        "Сера в сторон. (%)",
    "As_ext_%":       "Мышьяк в сторон. (%)",
    "Seq_ext_%":      "Серный эквивалент сторон. (%)",
    "Au_ext":         "Золото в сторон. (г/т)",
    "As_target":      "Целевой As (%)",
    "k":              "Коэффициент k",
    "yield_after_cond":"Выход после кондиционирования (%)",
    "Total_capacity_t":"Общая годовая мощность (т)",
    "Max_Q_base_t":   "Макс. масса осн. сырья (т)",
    "Max_total_Q_t":  "Макс. общий объём сырья (т)",
    "Q_base_t":       "Факт. масса осн. сырья (т)",
    "Mix_total_Q_t":  "Фактич. общая смесь (т)",
    "Mix_As_%":       "Итоговый As в смеси (%)",
    "Mix_Seq_%":      "Итоговый Seq в смеси (%)",
    "Total_Seq_mass_t":"Сумма серного эквивалента (т)",
    "Autoclaves_used":"Нужно автоклавов (шт)",
    "Mix_Au_g_t":     "Золото в смеси (г/т)",
    "Total_Au_kg":    "Всего золота (кг)",
    "Mass_kek_fk_t":  "КЕК ФК (т)"
}

def format_value(key, value):
    if value is None:
        return ""
    if key == "Mix_Au_g_t":
        return f"{value:.2f}".replace(".", ",")
    if "%" in key:
        return f"{value:.2f}"
    if key.endswith("_t"):
        return f"{value:.0f}"
    if key in ("Au_base", "Au_ext"):
        return f"{value:.2f}"
    if key.endswith("_kg"):
        return f"{value:.0f}"
    return f"{value:.2f}"

def main():
    ACCESS_CODE = "23101981"
    code = st.text_input("Введите код доступа", type="password")
    if code != ACCESS_CODE:
        st.warning("❌ Неверный код. Попробуйте снова")
        st.stop()

    # Исходные параметры
    work_hours_year = st.number_input("Рабочие часы в год", 0.0, 10000.0, 8000.0, 10.0)
    seq_prod_hour   = st.number_input("Производительность Seq, т/ч", 0.0, 500.0, 50.0, 0.1)

    mode_val = st.radio(
        "Режим расчёта:",
        [1, 2],
        format_func=lambda x: "1 – Два концентрата" if x == 1 else "2 – Один концентрат"
    )

    # Ввод базового концентрата
    st.markdown("### 🟩 Базовое сырьё")
    Au_base  = st.number_input("Золото в осн. (г/т)", 0.0, 200.0, 21.0, 0.1)
    S_base   = st.number_input("Сера в осн. (%)",    0.0, 100.0, 0.0, 0.01)
    As_base  = st.number_input("Мышьяк в осн. (%)",  0.0, 100.0, 0.0, 0.01)
    Seq_base = st.number_input("Seq осн. (%)",       0.0,  50.0, 25.8, 0.01)

    # Ввод стороннего концентрата
    if mode_val == 1:
        st.markdown("---")
        st.markdown("### 🟥 Стороннее сырьё")
        Au_ext  = st.number_input("Золото в сторон. (г/т)", 0.0, 200.0, 40.0, 0.1)
        S_ext   = st.number_input("Сера в сторон. (%)",    0.0, 100.0, 0.0, 0.01)
        As_ext  = st.number_input("Мышьяк в сторон. (%)",  0.0, 100.0, 0.0, 0.01)
        Seq_ext = st.number_input("Seq сторон. (%)",       0.0,  50.0, 30.7, 0.01)

        # Наши новые поля для Q_base и Q_ext
        st.markdown("---")
        st.markdown("### 📦 Объёмы сырья (т)")
        Q_base = st.number_input("Объём базового сырья, т",   min_value=0.0, step=1.0, value=0.0)
        Q_ext  = st.number_input("Объём стороннего сырья, т", min_value=0.0, step=1.0, value=0.0)
    else:
        Au_ext = S_ext = As_ext = Seq_ext = 0.0
        Q_base = Q_ext = 0.0

    st.markdown("---")
    st.markdown("### 🎯 Целевые параметры")
    As_target         = st.number_input("Целевой As (%)",                    0.0, 10.0, 0.0, 0.01)
    k                 = st.number_input("Коэффициент k",                    0.0, 10.0, 1.0, 0.01)
    yield_after_cond  = st.number_input("Выход после кондиционирования (%)", 0.0,100.0,70.4,0.01)

    submitted = st.button("Рассчитать")
    if submitted:
        # Заменяем 0 на None для передачи в функцию
        Qb = None if Q_base == 0 else Q_base
        Qe = None if Q_ext  == 0 else Q_ext

        # Автоподсчёт Seq, если пользователь оставил 0
        if Seq_base == 0 and (S_base or As_base):
            Seq_base = calculate_missing_seq_param(S_base, As_base, None, k)
            st.info(f"Рассчитан Seq осн.: {Seq_base:.2f}%")
        if mode_val == 1 and Seq_ext == 0 and (S_ext or As_ext):
            Seq_ext = calculate_missing_seq_param(S_ext, As_ext, None, k)
            st.info(f"Рассчитан Seq сторон.: {Seq_ext:.2f}%")

        # Основной вызов расчёта
        results = calc_fc_autoclave(
            name_base="Базовый",
            Au_base=Au_base, S_base=S_base, As_base=As_base, Seq_base=Seq_base,
            work_hours_year=work_hours_year, seq_productivity_per_hour=seq_prod_hour,
            name_ext="Сторонний", Au_ext=Au_ext, S_ext=S_ext, As_ext=As_ext, Seq_ext=Seq_ext,
            As_target=As_target, k=k, Q_base=Qb, Q_ext=Qe, yield_after_cond=yield_after_cond,
            mode=mode_val
        )
        st.success("Расчёт завершён")

        # Формируем и отображаем таблицу результатов
        skip_ext = {"S_ext_%","As_ext_%","Seq_ext_%","Au_ext","Max_Q_ext_t","Q_ext_required_t"}
        data = []
        for key, label in LABELS.items():
            if key not in results: continue
            if mode_val == 2 and key in skip_ext: continue
            raw = results[key]
            formatted = format_value(key, raw)
            if formatted.strip() in ("", "0", "0.0", "0,00"): continue
            data.append({"Показатель": label, "Значение": formatted})

        df = pd.DataFrame(data)
        st.dataframe(df)

if __name__ == "__main__":
    main()
