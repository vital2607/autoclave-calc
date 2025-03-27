# streamlit_app.py
import streamlit as st
import pandas as pd
from fc_autoclave_calc import calc_fc_autoclave, calculate_missing_seq_param
import io

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

TEMPLATES = {
    "ФК Маломыр": {
        "As_target": 3.0, "k": 0.371, "work_hours_year": 7500, "seq_productivity_per_hour": 4.07,
        "S_base": 21.24, "As_base": 3.82, "Seq_base": 0.0
    },
    "ФК Пионер": {
        "As_target": 2.5, "k": 0.35, "work_hours_year": 7200, "seq_productivity_per_hour": 3.8,
        "S_base": 0.0, "As_base": 0.8, "Seq_base": 30.7
    }
}

UNIT_FORMATS = {
    "т": lambda x: f"{x:.0f}", "%": lambda x: f"{x:.2f}", "г/т": lambda x: f"{x:.2f}",
    "шт": lambda x: f"{x:.0f}", "кг": lambda x: f"{x:.0f}", "": lambda x: f"{x:.3f}"
}

def format_value(key, value):
    if value is None:
        return ""
    if "%" in key:
        return UNIT_FORMATS["%"](value)
    elif key.endswith("_t"):
        return UNIT_FORMATS["т"](value)
    elif key.endswith("g_t"):
        return UNIT_FORMATS["г/т"](value)
    elif key.endswith("_kg"):
        return UNIT_FORMATS["кг"](value)
    elif key.endswith("_used"):
        return UNIT_FORMATS["шт"](value)
    else:
        return UNIT_FORMATS[""](value)

def main():
    st.set_page_config(page_title="Автоклавный расчёт", layout="wide")
    st.title("Расчёт флотоконцентрата и автоклавов")

    selected_template = "Концентрат 1"
    template = {}
    template = {}

    mode = st.radio("Режим расчёта", ["1 – Два концентрата", "2 – Один концентрат"])
    mode_val = 1 if mode.startswith("1") else 2

    with st.form("input_form"):
        reset = st.form_submit_button("Сбросить значения")
        if reset:
            st.experimental_rerun()
        st.subheader("Исходное сырьё")
        name_base = st.text_input("Имя исходного концентрата", value=selected_template)
        Au_base = st.number_input("Au осн. (г/т)", min_value=0.0)
        S_base = st.number_input("S осн. (%)", min_value=0.0, value=template.get("S_base", 0.0))
        As_base = st.number_input("As осн. (%)", min_value=0.0, value=template.get("As_base", 0.0))
        Seq_base = st.number_input("Seq осн. (%)", min_value=0.0, value=template.get("Seq_base", 0.0))

        st.subheader("Параметры автоклава")
        work_hours_year = st.number_input("Рабочих часов в году", value=7500)
        seq_productivity_per_hour = st.number_input("Производительность автоклава (т/ч)", value=4.07)

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
        As_target = st.number_input("Целевой As (%)", min_value=0.0, value=3.0)
        k = st.number_input("Коэффициент k", value=0.371)
        Q_base = st.number_input("Q осн. (т/год) [опц.]", value=0.0)
        Q_ext = st.number_input("Q сторон. (т/год) [опц.]", value=0.0)
        yield_after_cond = st.number_input("Выход после кондиционирования (%)", value=100.0)

        submitted = st.form_submit_button("Рассчитать")

    if submitted:
        Q_base = Q_base if Q_base > 0 else None
        Q_ext = Q_ext if Q_ext > 0 else None

        # авторасчёт серного эквивалента если он = 0
        if Seq_base == 0 and (S_base > 0 or As_base > 0):
            Seq_base = calculate_missing_seq_param(S_base, As_base, None, k)
            st.info(f"Рассчитан серный эквивалент: {Seq_base:.2f}%")

        if Seq_base == 0:
            st.warning("Серный эквивалент = 0. Расчёт невозможен. Укажите S и As или Seq вручную.")
            return

        results = calc_fc_autoclave(
            name_base=name_base, Au_base=Au_base, S_base=S_base, As_base=As_base, Seq_base=Seq_base,
            work_hours_year=work_hours_year, seq_productivity_per_hour=seq_productivity_per_hour,
            name_ext=name_ext, Au_ext=Au_ext, S_ext=S_ext, As_ext=As_ext, Seq_ext=Seq_ext,
            As_target=As_target, k=k, Q_base=Q_base, Q_ext=Q_ext,
            yield_after_cond=yield_after_cond, mode=mode_val
        )

        st.success("Расчёт завершён")
        data = []
        for key in [
            "S_base_%", "As_base_%", "Seq_base_%", "Au_base",
            "S_ext_%", "As_ext_%", "Seq_ext_%", "Au_ext",
            "As_target", "k", "yield_after_cond",
            "Total_capacity_t", "Max_Q_base_t", "Max_Q_ext_t", "Max_total_Q_t",
            "Q_base_t", "Q_ext_required_t", "Mix_total_Q_t",
            "Mix_As_%", "Mix_Seq_%", "Total_Seq_mass_t", "Autoclaves_used",
            "Mix_Au_g_t", "Total_Au_kg", "Mass_kek_fk_t"
        ]:
            if key in results:
                value = results[key]
                formatted = format_value(key, value)
                if str(formatted).strip() not in ('0', '0.0', '0.00'):
                    label = LABELS.get(key, key)
                    data.append({"Показатель": label, "Значение": formatted})

        df = pd.DataFrame(data)
        st.dataframe(df)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="autoclave")
            workbook = writer.book
            worksheet = writer.sheets["autoclave"]

            format1 = workbook.add_format({"bg_color": "#DDEBF7"})
            format2 = workbook.add_format({"bg_color": "#FCE4D6"})

            for row in range(1, len(df) + 1):
                fmt = format1 if row % 2 == 0 else format2
                worksheet.set_row(row, None, fmt)

        st.download_button(
            label="Скачать как Excel (.xlsx)",
            data=buffer,
            file_name="autoclave_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == '__main__':
    main()
