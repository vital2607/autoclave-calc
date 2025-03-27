# streamlit_app.py
import streamlit as st
import pandas as pd
from fc_autoclave_calc import calc_fc_autoclave
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
        "Au_base": 1.2, "S_base": 35.0, "As_base": 2.5, "Seq_base": 36.0,
        "Au_ext": 0.9, "S_ext": 30.0, "As_ext": 5.0, "Seq_ext": 31.9
    },
    "ФК Пионер": {
        "As_target": 2.5, "k": 0.35, "work_hours_year": 7200, "seq_productivity_per_hour": 3.8,
        "Au_base": 1.1, "S_base": 32.0, "As_base": 2.2, "Seq_base": 32.8,
        "Au_ext": 0.8, "S_ext": 27.0, "As_ext": 4.0, "Seq_ext": 28.4
    },
    "ФК Стороний": {
        "As_target": 3.2, "k": 0.4, "work_hours_year": 8000, "seq_productivity_per_hour": 5.0,
        "Au_base": 1.0, "S_base": 33.0, "As_base": 2.8, "Seq_base": 34.0,
        "Au_ext": 0.7, "S_ext": 25.0, "As_ext": 4.5, "Seq_ext": 26.7
    }
}

# Форматирование чисел
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

    st.subheader("Шаблон параметров")
    selected_template = st.selectbox("Выберите шаблон:", list(TEMPLATES.keys()), index=0)
    template = TEMPLATES[selected_template]

    mode = st.radio("Режим расчёта", ["1 – Два концентрата", "2 – Один концентрат"])
    mode_val = 1 if mode.startswith("1") else 2

    with st.form("input_form"):
        st.subheader("Исходное сырьё")
        name_base = st.text_input("Имя исходного концентрата", "Концентрат 1")
        Au_base = st.number_input("Au осн. (г/т)", min_value=0.0, value=template["Au_base"])
        S_base = st.number_input("S осн. (%)", min_value=0.0, value=template["S_base"])
        As_base = st.number_input("As осн. (%)", min_value=0.0, value=template["As_base"])
        Seq_base = st.number_input("Seq осн. (%)", min_value=0.0, value=template["Seq_base"])

        st.subheader("Параметры автоклава")
        work_hours_year = st.number_input("Рабочих часов в году", value=template["work_hours_year"])
        seq_productivity_per_hour = st.number_input("Производительность автоклава (т/ч)", value=template["seq_productivity_per_hour"])

        if mode_val == 1:
            st.subheader("Стороннее сырьё")
            name_ext = st.text_input("Имя стороннего концентрата", "Концентрат 2")
            Au_ext = st.number_input("Au сторон. (г/т)", min_value=0.0, value=template["Au_ext"])
            S_ext = st.number_input("S сторон. (%)", min_value=0.0, value=template["S_ext"])
            As_ext = st.number_input("As сторон. (%)", min_value=0.0, value=template["As_ext"])
            Seq_ext = st.number_input("Seq сторон. (%)", min_value=0.0, value=template["Seq_ext"])
        else:
            name_ext, Au_ext, S_ext, As_ext, Seq_ext = None, None, None, None, None

        st.subheader("Целевые параметры")
        As_target = st.number_input("Целевой As (%)", min_value=0.0, value=template["As_target"])
        k = st.number_input("Коэффициент k", value=template["k"])
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
            formatted = format_value(key, value)
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
