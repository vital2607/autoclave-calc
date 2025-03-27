# streamlit_app.py — обновлено с акцентом на точный расчёт как в эталоне
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

UNIT_FORMATS = {
    "%": lambda x: f"{x:.2f}", "т": lambda x: f"{x:.0f}", "г/т": lambda x: f"{x:.2f}",
    "шт": lambda x: f"{x:.2f}", "кг": lambda x: f"{x:.0f}", "": lambda x: f"{x:.3f}"
}

def format_value(key, value):
    if value is None:
        return ""
    if "%" in key:
        return UNIT_FORMATS["%"](value)
    elif key.endswith("_t"):
        return UNIT_FORMATS["т"](value)
    elif key.endswith("g_t"):
        return f"{value:.2f}"
    elif key.endswith("_kg"):
        return UNIT_FORMATS["кг"](value)
    elif key.endswith("_used"):
        return UNIT_FORMATS["шт"](value)
    else:
        return UNIT_FORMATS[""](value)

st.set_page_config(page_title="Автоклавный расчёт", layout="wide")
def main():
    ACCESS_CODE = "23101981"  # ← установи здесь свой код доступа


    code = st.text_input("Введите код доступа", type="password")
    if code != ACCESS_CODE:
        st.warning("❌ Неверный код. Попробуйте снова")
        st.stop()
    
    mode_val = st.radio("Режим расчёта:", options=[1, 2], format_func=lambda x: "1 – Два концентрата" if x == 1 else "2 – Один концентрат")
    reset = st.button("Сбросить значения")
    if reset:
        st.experimental_rerun()

    st.title("Расчёт флотоконцентрата и автоклавов")
    with st.form("input_form"):
        st.subheader("Исходное сырьё")
        name_base = st.text_input("Имя исходного концентрата", value="Концентрат 1")
        col_au1, col_au2 = st.columns([3, 1])
        with col_au1:
            Au_base = st.slider("Au осн. (г/т)", min_value=0.0, max_value=200.0, value=0.0, step=0.1, key="slider_Au_base")
        with col_au2:
            Au_base = st.number_input(" ", min_value=0.0, max_value=200.0, value=Au_base, step=0.1, key="input_Au_base")
        col_sb1, col_sb2 = st.columns([3, 1])
        with col_sb1:
            S_base = st.slider("S осн. (%)", min_value=0.0, max_value=50.0, value=0.0, step=0.01, key="slider_S_base")
        with col_sb2:
            S_base = st.number_input(" ", min_value=0.0, max_value=100.0, value=S_base, step=0.01, key="input_S_base")
        col_ab1, col_ab2 = st.columns([3, 1])
        with col_ab1:
            As_base_val = st.slider("As осн. (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.01, key="slider_As_base")
        with col_ab2:
            As_base = st.number_input(" ", min_value=0.0, max_value=30.0, value=As_base_val, step=0.01, key="input_As_base")
        col_sbseq1, col_sbseq2 = st.columns([3, 1])
        with col_sbseq1:
            Seq_base = st.slider("Seq осн. (%)", min_value=0.0, max_value=50.0, value=0.0, step=0.01, key="slider_Seq_base")
        with col_sbseq2:
            Seq_base = st.number_input(" ", min_value=0.0, max_value=100.0, value=Seq_base, step=0.01, key="input_Seq_base", help="Если не задан — будет рассчитан автоматически")

        st.subheader("Параметры автоклава")
        col_hours1, col_hours2 = st.columns([3, 1])
        with col_hours1:
            col_hours1, col_hours2 = st.columns([3, 1])
        with col_hours1:
            work_hours_year_val = st.slider("Рабочих часов в году", min_value=1000, max_value=9000, value=7500, step=100, key="slider_hours")
        with col_hours2:
            work_hours_year = st.number_input(" ", min_value=1000, max_value=9000, value=work_hours_year_val, step=100, key="input_hours")
        col_prod1, col_prod2 = st.columns([3, 1])
        with col_prod1:
            col_prod1, col_prod2 = st.columns([3, 1])
        with col_prod1:
            seq_productivity_per_hour_val = st.slider("Производительность автоклава (т/ч)", min_value=0.1, max_value=10.0, value=4.07, step=0.01, key="slider_prod")
        with col_prod2:
            seq_productivity_per_hour = st.number_input(" ", min_value=0.1, max_value=10.0, value=seq_productivity_per_hour_val, step=0.01, key="input_prod")

        if mode_val == 1:
            st.subheader("Стороннее сырьё")
            name_ext = st.text_input("Имя стороннего концентрата", value="Концентрат 2")
            col_au_ext1, col_au_ext2 = st.columns([3, 1])
            with col_au_ext1:
                Au_ext = st.slider("Au сторон. (г/т)", min_value=0.0, max_value=200.0, value=0.0, step=0.1, key="slider_Au_ext")
            with col_au_ext2:
                Au_ext = st.number_input(" ", min_value=0.0, max_value=200.0, value=Au_ext, step=0.1, key="input_Au_ext")
            col_se1, col_se2 = st.columns([3, 1])
            with col_se1:
                S_ext = st.slider("S сторон. (%)", min_value=0.0, max_value=50.0, value=0.0, step=0.01, key="slider_S_ext")
            with col_se2:
                S_ext = st.number_input(" ", min_value=0.0, max_value=100.0, value=S_ext, step=0.01, key="input_S_ext")
            col_ae1, col_ae2 = st.columns([3, 1])
            with col_ae1:
                As_ext = st.slider("As сторон. (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.01, key="slider_As_ext")
            with col_ae2:
                As_ext = st.number_input(" ", min_value=0.0, max_value=100.0, value=As_ext, step=0.01, key="input_As_ext")
            col_seqe1, col_seqe2 = st.columns([3, 1])
            with col_seqe1:
                Seq_ext = st.slider("Seq сторон. (%)", min_value=0.0, max_value=50.0, value=0.0, step=0.01, key="slider_Seq_ext")
            with col_seqe2:
                Seq_ext = st.number_input(" ", min_value=0.0, max_value=50.0, value=Seq_ext, step=0.01, key="input_Seq_ext")
        else:
            name_ext = ""
            Au_ext = 0.0
            S_ext = 0.0
            As_ext = 0.0
            Seq_ext = 0.0

        st.subheader("Целевые параметры")
        col_ast1, col_ast2 = st.columns([3, 1])
        with col_ast1:
            As_target = st.slider("Целевой As (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.01, key="slider_As_target")
        with col_ast2:
            As_target = st.number_input(" ", min_value=0.0, max_value=10.0, value=As_target, step=0.01, key="input_As_target")
        col_k1, col_k2 = st.columns([3, 1])
        with col_k1:
            k_val = st.slider("Коэффициент k", min_value=0.0, max_value=1.0, value=0.371, step=0.001, key="slider_k")
        with col_k2:
            k = st.number_input(" ", min_value=0.0, max_value=1.0, value=k_val, step=0.001, key="input_k2")
        st.number_input("Коэффициент k", min_value=0.0, max_value=1.0, value=k, step=0.001, key="input_k")
        col_qb1, col_qb2 = st.columns([3, 1])
        with col_qb1:
            Q_base = st.slider("Q осн. (т/год)", min_value=0.0, max_value=500000.0, value=140000.0, step=1000.0, key="slider_Q_base")
        with col_qb2:
            Q_base = st.number_input(" ", min_value=0.0, max_value=500000.0, value=Q_base, step=1000.0, key="input_Q_base")
        col_qe1, col_qe2 = st.columns([3, 1])
        with col_qe1:
            Q_ext_val = st.slider("Q сторон. (т/год)", min_value=0.0, max_value=500000.0, value=38500.0, step=1000.0, key="slider_Q_ext")
        with col_qe2:
            Q_ext = st.number_input(" ", min_value=0.0, max_value=500000.0, value=Q_ext_val, step=1000.0, key="input_Q_ext")
        col_y1, col_y2 = st.columns([3, 1])
        with col_y1:
            yield_after_cond = st.slider("Выход после кондиционирования (%)", min_value=0.0, max_value=100.0, value=70.4, step=0.1, key="slider_yield")
        with col_y2:
            yield_after_cond = st.number_input(" ", min_value=0.0, max_value=100.0, value=yield_after_cond, step=0.1, key="input_yield")

        submitted = st.form_submit_button("Рассчитать")

    with st.spinner("Выполняется расчёт..."):
        if submitted:
            Q_base = Q_base if Q_base > 0 else None
        Q_ext = Q_ext if Q_ext > 0 else None

        if Seq_base == 0 and (S_base > 0 or As_base > 0):
            Seq_base = calculate_missing_seq_param(S_base, As_base, None, k)
            st.info(f"Рассчитан серный эквивалент: {Seq_base:.2f}%")

        if Seq_ext == 0 and (S_ext > 0 or As_ext > 0):
            Seq_ext = calculate_missing_seq_param(S_ext, As_ext, None, k)
            st.info(f"Рассчитан серный эквивалент стороннего: {Seq_ext:.2f}%")

        results = calc_fc_autoclave(
            name_base=name_base, Au_base=Au_base, S_base=S_base, As_base=As_base, Seq_base=Seq_base,
            work_hours_year=work_hours_year, seq_productivity_per_hour=seq_productivity_per_hour,
            name_ext=name_ext, Au_ext=Au_ext, S_ext=S_ext, As_ext=As_ext, Seq_ext=Seq_ext,
            As_target=As_target, k=k, Q_base=Q_base, Q_ext=Q_ext,
            yield_after_cond=yield_after_cond, mode=mode_val
        )

        st.success("Расчёт завершён")
        data = []
        for key in LABELS:
            if key in results:
                if mode_val == 2 and key in ["S_ext_%", "As_ext_%", "Seq_ext_%", "Au_ext", "Max_Q_ext_t", "Q_ext_required_t"]:
                    continue  # пропуск стороннего сырья в режиме 2
                value = results[key]
                formatted = format_value(key, value)
                label = LABELS[key]
                if str(formatted).strip() not in ('0', '0.0', '0.00'):
                    data.append({"Показатель": label, "Значение": formatted})

        df = pd.DataFrame(data)
        st.dataframe(df)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_export = df.copy()
            if mode_val == 2:
                df_export = df_export[~df_export["Показатель"].isin([
                    "Сера в сторон. (%)", "Мышьяк в сторон. (%)", "Серный эквивалент сторон. (%)", "Золото в сторон. (г/т)",
                    "Макс. масса сторон. сырья (т)", "Факт. масса сторон. сырья (т)"
                ])]
            worksheet_name = "autoclave"
            worksheet_title = f"Результаты расчёта ({'2 – Один концентрат' if mode_val == 2 else '1 – Два концентрата'})"
            df_export.to_excel(writer, index=False, sheet_name=worksheet_name, startrow=2)
            worksheet = writer.sheets[worksheet_name]
            worksheet.write("A1", worksheet_title)
            workbook = writer.book
            worksheet = writer.sheets["autoclave"]
            format1 = workbook.add_format({"bg_color": "#DDEBF7"})
            format2 = workbook.add_format({"bg_color": "#FCE4D6"})
            for row in range(1, len(df_export) + 1):
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
