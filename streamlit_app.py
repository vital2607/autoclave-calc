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
    "%": lambda x: f"{x:.2f}",
    "т": lambda x: f"{x:.0f}",
    "г/т": lambda x: f"{x:.2f}",
    "шт": lambda x: f"{x:.2f}",
    "кг": lambda x: f"{x:.0f}",
    "": lambda x: f"{x:.3f}"
}

def format_value(key, value):
    if value is None:
        return ""
    # Сразу обрабатываем Mix_Au_g_t — два знака и запятая
    if key == "Mix_Au_g_t":
        return f"{value:.2f}".replace(".", ",")
    if "%" in key:
        return UNIT_FORMATS["%"](value)
    elif key.endswith("_t"):
        return UNIT_FORMATS["т"](value)
    elif key in ("Au_base", "Au_ext"):
        return f"{value:.2f}"
    elif key.endswith("_kg"):
        return UNIT_FORMATS["кг"](value)
    elif key.endswith("_used"):
        return UNIT_FORMATS["шт"](value)
    else:
        return UNIT_FORMATS[""](value)

st.set_page_config(page_title="Автоклавный расчёт", layout="wide")

def main():
    ACCESS_CODE = "23101981"
    code = st.text_input("Введите код доступа", type="password")
    if code != ACCESS_CODE:
        st.warning("❌ Неверный код. Попробуйте снова")
        st.stop()

    mode_val = st.radio(
        "Режим расчёта:",
        options=[1, 2],
        format_func=lambda x: "1 – Два концентрата" if x == 1 else "2 – Один концентрат"
    )
    if st.button("Сбросить значения"):
        st.experimental_rerun()

    st.title("Расчёт флотоконцентрата и автоклавов")
    with st.form("input_form"):
        st.markdown("### 🟦 Исходное сырьё")
        name_base = st.text_input("Имя исходного концентрата", value="Концентрат 1")
        Au_base = st.number_input("Золото в осн. (г/т)", 0.0, 200.0, 0.0, 0.1)
        S_base  = st.number_input("Сера в осн. (%)",        0.0, 100.0, 0.0, 0.01)
        As_base = st.number_input("Мышьяк в осн. (%)",      0.0, 30.0,  0.0, 0.01)
        Seq_base= st.number_input("Серный эквивалент осн. (%)",0.0,100.0,0.0,0.01)

        st.markdown("---")
        st.markdown("### ⚙️ Параметры автоклава")
        work_hours_year         = st.number_input("Рабочих часов в году", 1000,9000,7500,100)
        seq_productivity_per_hour = st.number_input("Производительность автоклава (т/ч)", 0.1,10.0,4.07,0.01)

        if mode_val == 1:
            st.markdown("---")
            st.markdown("### 🟥 Стороннее сырьё")
            name_ext= st.text_input("Имя стороннего концентрата", value="Концентрат 2")
            Au_ext  = st.number_input("Золото в сторон. (г/т)", 0.0,200.0,0.0,0.1)
            S_ext   = st.number_input("Сера в сторон. (%)",    0.0,100.0,0.0,0.01)
            As_ext  = st.number_input("Мышьяк в сторон. (%)",  0.0,100.0,0.0,0.01)
            Seq_ext = st.number_input("Серный эквивалент сторон. (%)",0.0,50.0,0.0,0.01)
        else:
            name_ext = ""
            Au_ext = S_ext = As_ext = Seq_ext = 0.0

        st.markdown("---")
        st.markdown("### 🎯 Целевые параметры")
        As_target = st.number_input("Целевой As (%)", 0.0,10.0,3.0,0.01)
        k         = st.number_input("Коэффициент k",   0.0,1.0,0.371,0.001)
        Q_base    = st.number_input("Q осн. (т/год)",   0.0,500000.0,140000.0,1000.0)
        Q_ext     = st.number_input("Q сторон. (т/год)",0.0,500000.0,38500.0,1000.0)
        yield_after_cond = st.number_input("Выход после кондиционирования (%)",0.0,100.0,70.4,0.1)
        submitted = st.form_submit_button("Рассчитать")

    if submitted:
        Q_base = None if Q_base == 0 else Q_base
        Q_ext  = None if Q_ext  == 0 else Q_ext

        if Seq_base == 0 and (S_base or As_base):
            Seq_base = calculate_missing_seq_param(S_base, As_base, None, k)
            st.info(f"Рассчитан серный эквивалент: {Seq_base:.2f}%")
        if Seq_ext == 0 and mode_val == 1 and (S_ext or As_ext):
            Seq_ext = calculate_missing_seq_param(S_ext, As_ext, None, k)
            st.info(f"Рассчитан серный эквивалент стороннего: {Seq_ext:.2f}%")

        results = calc_fc_autoclave(
            name_base, Au_base, S_base, As_base, Seq_base,
            work_hours_year, seq_productivity_per_hour,
            name_ext, Au_ext, S_ext, As_ext, Seq_ext,
            As_target, k, Q_base, Q_ext, yield_after_cond, mode_val
        )
        st.success("Расчёт завершён")

        data = []
        for key in LABELS:
            if key not in results:
                continue
            value = results[key]
            formatted = format_value(key, value)
            label = LABELS[key]
            if formatted not in ("", "0", "0.0", "0.00") or key == "Mix_Au_g_t":
                data.append({"Показатель": label, "Значение": formatted})

        df = pd.DataFrame(data)

        # Дополнительное безопасное форматирование Mix_Au_g_t (не обязательно)
        mask = df["Показатель"] == "Золото в смеси (г/т)"
        if mask.any():
            df.loc[mask, "Значение"] = (
                df.loc[mask, "Значение"]
                  .str.replace(",", ".")
                  .astype(float)
                  .map(lambda x: f"{x:.2f}".replace(".", ","))
            )

        st.dataframe(df)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_export = df.copy()
            df_export.to_excel(writer, index=False, sheet_name="autoclave", startrow=2)
            ws = writer.sheets["autoclave"]
            ws.write("A1", f"Результаты расчёта ({'2 – Один концентрат' if mode_val==2 else '1 – Два концентрата'})")
            fmt1 = writer.book.add_format({"bg_color": "#DDEBF7"})
            fmt2 = writer.book.add_format({"bg_color": "#FCE4D6"})
            for ri in range(1, len(df_export)+1):
                ws.set_row(ri, None, fmt1 if ri % 2 == 0 else fmt2)

        st.download_button(
            "Скачать как Excel (.xlsx)",
            data=buffer,
            file_name="autoclave_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
