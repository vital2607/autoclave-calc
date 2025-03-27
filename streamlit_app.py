# streamlit_app.py
import streamlit as st
import pandas as pd
from fc_autoclave_calc import calc_fc_autoclave

# Расшифровка переменных
LABELS = {
    "S_base_%": "Сера в осн. (%)",
    "As_base_%": "Мышьяк в осн. (%)",
    "Seq_base_%": "Серный эквивалент осн. (%)",
    "Au_base": "Золото в осн. (г/т)",
    "S_ext_%": "Сера в сторон. (%)",
    "As_ext_%": "Мышьяк в сторон. (%)",
    "Seq_ext_%": "Серный эквивалент сторон. (%)",
    "Au_ext": "Золото в сторон. (г/т)",
    "As_target": "Целевой As (%)",
    "k": "Коэффициент k",
    "yield_after_cond": "Выход после кондиционирования (%)",
    "Total_capacity_t": "Общая годовая мощность (т)",
    "Max_Q_base_t": "Макс. масса осн. сырья (т)",
    "Max_Q_ext_t": "Макс. масса сторон. сырья (т)",
    "Max_total_Q_t": "Макс. общий объём сырья (т)",
    "Q_base_t": "Факт. масса осн. сырья (т)",
    "Q_ext_required_t": "Факт. масса сторон. сырья (т)",
    "Mix_total_Q_t": "Фактич. общая смесь (т)",
    "Mix_As_%": "Итоговый As в смеси (%)",
    "Mix_Seq_%": "Итоговый Seq в смеси (%)",
    "Total_Seq_mass_t": "Сумма серного эквивалента (т)",
    "Autoclaves_used": "Нужно автоклавов (шт)",
    "Mix_Au_g_t": "Золото в смеси (г/т)",
    "Total_Au_kg": "Всего золота (кг)",
    "Mass_kek_fk_t": "КЕК ФК (т)"
}

def main():
    st.set_page_config(page_title="Автоклавный расчёт", layout="wide")
    st.title("Расчёт флотоконцентрата и автоклавов")

    mode = st.radio("Режим расчёта", ["1 – Два концентрата", "2 – Один концентрат"])
    mode_val = 1 if mode.startswith("1") else 2

    with st.form("input_form"):
        st.subheader("Исходное сырьё")
        name_base = st.text_input("Имя исходного концентрата", "Концентрат 1")
        Au_base = st.number_input("Au осн. (г/т)", min_value=0.0)
        S_base = st.number_input("S осн. (%)", min_value=0.0)
        As_base = st.number_input("As осн. (%)", min_value=0.0)
        Seq_base = st.number_input("Seq осн. (%)", min_value=0.0)

        st.subheader("Параметры автоклава")
        work_hours_year = st.number_input("Рабочих часов в году", value=8000)
        seq_productivity_per_hour = st.number_input("Производительность автоклава (т/ч)", value=5.0)

        if mode_val == 1:
            st.subheader("Стороннее сырьё")
            name_ext = st.text_input("Имя стороннего концентрата", "Концентрат 2")
            Au_ext = st.number_input("Au сторон. (г/т)", min_value=0.0)
            S_ext = st.number_input("S сторон. (%)", min_value=0.0)
            As_ext = st.number_input("As сторон. (%)", min_value=0.0)
            Seq_ext = st.number_input("Seq сторон. (%)", min_value=0.0)
        else:
            name_ext, Au_ext, S_ext, As_ext, Seq_ext = None, None, None, None, None

        st.subheader("Целевые параметры")
        As_target = st.number_input("Целевой As (%)", min_value=0.0)
        k = st.number_input("Коэффициент k", value=1.0)
        Q_base = st.number_input("Q осн. (т/год) [опц.]", value=0.0)
        Q_ext = st.number_input("Q сторон. (т/год) [опц.]", value=0.0)
        yield_after_cond = st.number_input("Выход после кондиционирования (%)", value=100.0)

        submitted = st.form_submit_button("Рассчитать")

    if submitted:
        Q_base = Q_base if Q_base > 0 else None
        Q_ext = Q_ext if Q_ext > 0 else None

        results = calc_fc_autoclave(
            name_base=name_base, Au_base=Au_base, S_base=S_base, As_base=As_base, Seq_base=Seq_base,
            work_hours_year=work_hours_year, seq_productivity_per_hour=seq_productivity_per_hour,
            name_ext=name_ext, Au_ext=Au_ext, S_ext=S_ext, As_ext=As_ext, Seq_ext=Seq_ext,
            As_target=As_target, k=k, Q_base=Q_base, Q_ext=Q_ext,
            yield_after_cond=yield_after_cond, mode=mode_val
        )

        st.success("Расчёт завершён")
        data = []
        for key, value in results.items():
            label = LABELS.get(key, key)
            data.append({"Показатель": label, "Значение": value})

        df = pd.DataFrame(data)
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Скачать как CSV", data=csv, file_name="autoclave_result.csv", mime="text/csv")

if __name__ == '__main__':
    main()
