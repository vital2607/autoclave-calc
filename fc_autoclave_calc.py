import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import traceback
import os
import sys

# Закрытие сплэш-экрана PyInstaller (если он есть)
if hasattr(sys, '_MEIPASS'):
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

# Логирование ошибок
def log_error_to_file(error_message):
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write(error_message + "\n\n")

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

# Расчёт недостающих Seq/S/As
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

# Основной расчёт
def calc_fc_autoclave(name_base, Au_base, S_base, As_base, Seq_base,
                      work_hours_year, seq_productivity_per_hour,
                      name_ext, Au_ext, S_ext, As_ext, Seq_ext,
                      As_target, k=1.0, Q_base=None, Q_ext=None,
                      yield_after_cond=100.0, mode=1):
    results = {}
    # Исходное сырье
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
    mass_kek_fk = mix_total_q * (yield_after_cond / 100.0)
    Au_mix = ((Au_base or 0.0) * Q_base + (Au_ext or 0.0) * Q_ext_required) / mix_total_q if mix_total_q else 0.0
    total_au_mass = Au_mix * mix_total_q / 1000

    results.update({
        'Max_Q_base_t': Q_base_max,
        'Max_Q_ext_t': Q_ext_required_max if mode == 1 else 0.0,
        'Max_total_Q_t': max_total_q,
        'Q_base_t': Q_base,
        'Q_ext_required_t': Q_ext_required if mode == 1 else 0.0,
        'Mix_total_Q_t': mix_total_q,
        'Mix_As_%': As_mix,
        'Mix_Seq_%': Seq_mix,
        'Total_Seq_mass_t': total_seq_mass,
        'Autoclaves_used': round(num_autoclaves, 2),
        'Mix_Au_g_t': Au_mix,
        'Total_Au_kg': round(total_au_mass, 0),
        'Mass_kek_fk_t': mass_kek_fk
    })

    return results

# Продолжение → GUI в следующем сообщении?
def run_gui():
    def calculate_and_save():
        try:
            inputs_raw = {key: entries[key].get().replace(',', '.') for key in entries}
            Q_base_raw = inputs_raw.pop('Q_base', '')
            Q_ext_raw = inputs_raw.pop('Q_ext', '')
            yield_raw = inputs_raw.pop('yield_after_cond', '100')
            Q_base = float(Q_base_raw) if Q_base_raw else None
            Q_ext = float(Q_ext_raw) if Q_ext_raw else None
            yield_after_cond = float(yield_raw) if yield_raw else 100.0

            inputs = {}
            for key, value in inputs_raw.items():
                if key not in ['name_base', 'name_ext']:
                    inputs[key] = float(value) if value else None
                else:
                    inputs[key] = value

            mode = mode_var.get()
            results = calc_fc_autoclave(
                **inputs, Q_base=Q_base, Q_ext=Q_ext,
                yield_after_cond=yield_after_cond, mode=mode
            )

            output.delete('1.0', tk.END)
            rows = []
            def append_row(desc, key, unit):
                val = results.get(key)
                if val is not None:
                    formatted = format_value(val, unit)
                    output.insert(tk.END, f"{desc} ({key}): {formatted} {unit}\n")
                    rows.append({'Описание': desc, 'Обозначение': key, 'Значение': formatted, 'Ед. изм.': unit})

            output.insert(tk.END, f"Режим: {'Два концентрата' if mode == 1 else 'Один концентрат'}\n\n")
            append_row("Целевой As", 'As_target', '%')
            append_row("Коэффициент k", 'k', '')
            output.insert(tk.END, f"Выход после кондиционирования (yield_after_cond): {format_value(yield_after_cond, '%')} %\n\n")

            output.insert(tk.END, f"{inputs['name_base']}\n")
            append_row("Содержание серы в исходном", 'S_base_%', '%')
            append_row("Содержание мышьяка в исходном", 'As_base_%', '%')
            append_row("Серный эквивалент исходного", 'Seq_base_%', '%')
            append_row("Содержание золота в исходном", 'Au_base', 'г/т')
            output.insert(tk.END, "\n")

            if mode == 1:
                output.insert(tk.END, f"{inputs['name_ext']}\n")
                append_row("Содержание серы в стороннем", 'S_ext_%', '%')
                append_row("Содержание мышьяка в стороннем", 'As_ext_%', '%')
                append_row("Серный эквивалент стороннего", 'Seq_ext_%', '%')
                append_row("Содержание золота в стороннем", 'Au_ext', 'г/т')
                output.insert(tk.END, "\n")

            append_row("Допустимая масса осн. сырья", 'Max_Q_base_t', 'т')
            if mode == 1:
                append_row("Допустимая масса сторон. сырья", 'Max_Q_ext_t', 'т')
            append_row("Максимальная сумма сырья", 'Max_total_Q_t', 'т')
            append_row("Фактическая масса осн. сырья", 'Q_base_t', 'т')
            if mode == 1:
                append_row("Фактическая масса стороннего сырья", 'Q_ext_required_t', 'т')
            append_row("Общая фактическая смесь", 'Mix_total_Q_t', 'т')
            append_row("Итоговый As в смеси", 'Mix_As_%', '%')
            append_row("Итоговый Seq в смеси", 'Mix_Seq_%', '%')
            append_row("Сумма серного эквивалента", 'Total_Seq_mass_t', 'т')
            append_row("Сколько автоклавов нужно", 'Autoclaves_used', 'шт')
            append_row("Среднее содержание золота в смеси", 'Mix_Au_g_t', 'г/т')
            append_row("Всего золота", 'Total_Au_kg', 'кг')
            append_row("КЕК ФК (после кондиционирования)", 'Mass_kek_fk_t', 'т')

            save_option = var_save.get()
            if save_option != 'None':
                file_path = filedialog.asksaveasfilename(defaultextension=f".{save_option}",
                                                         filetypes=[(f"{save_option.upper()} files", f"*.{save_option}")])
                if file_path:
                    df = pd.DataFrame(rows)
                    if save_option == 'csv':
                        df.to_csv(file_path, sep=';', index=False)
                    elif save_option == 'xlsx':
                        df.to_excel(file_path, index=False)
                    messagebox.showinfo("Успех", f"Файл сохранён: {file_path}")
                    if messagebox.askyesno("Открыть файл?", "Открыть сохранённый файл?"):
                        os.startfile(file_path)

        except Exception as e:
            error_msg = f"Ошибка: {e}\n" + traceback.format_exc()
            output.delete('1.0', tk.END)
            output.insert(tk.END, error_msg)
            log_error_to_file(error_msg)
    root = tk.Tk()
    root.title("Расчёт флотоконцентрата и автоклавов")

    params = [
        ('name_base', 'Имя исходного концентрата'),
        ('Au_base', 'Au осн. (г/т)'), ('S_base', 'S осн. (%)'),
        ('As_base', 'As осн. (%)'), ('Seq_base', 'Seq осн. (%)'),
        ('work_hours_year', 'Рабочих часов в году'),
        ('seq_productivity_per_hour', 'Производительность автоклава (т/ч)'),
        ('name_ext', 'Имя стороннего концентрата'),
        ('Au_ext', 'Au сторон. (г/т)'), ('S_ext', 'S сторон. (%)'),
        ('As_ext', 'As сторон. (%)'), ('Seq_ext', 'Seq сторон. (%)'),
        ('As_target', 'Целевой As (%)'), ('k', 'Коэффициент k'),
        ('Q_base', 'Q осн. (т/год) [опц.]'), ('Q_ext', 'Q сторон. (т/год) [опц.]'),
        ('yield_after_cond', 'Выход после кондиционирования (%)')
    ]

    entries = {}
    for idx, (key, label) in enumerate(params):
        tk.Label(root, text=label).grid(row=idx, column=0, sticky='w')
        e = tk.Entry(root, width=30)
        e.grid(row=idx, column=1)
        entries[key] = e

    # Сохранение
    tk.Label(root, text="Сохранить в файл:").grid(row=len(params), column=0, sticky='w')
    var_save = tk.StringVar(value='None')
    tk.OptionMenu(root, var_save, 'None', 'csv', 'xlsx').grid(row=len(params), column=1, sticky='w')

    # Переключение режимов
    tk.Label(root, text="Режим расчёта:").grid(row=len(params)+1, column=0, sticky='w')
    mode_var = tk.IntVar(value=1)
    tk.Radiobutton(root, text="1 – Два концентрата", variable=mode_var, value=1).grid(row=len(params)+1, column=1, sticky='w')
    tk.Radiobutton(root, text="2 – Один концентрат", variable=mode_var, value=2).grid(row=len(params)+2, column=1, sticky='w')

    # Кнопка расчёта
    tk.Button(root, text="Рассчитать", command=calculate_and_save, bg="lightblue").grid(row=len(params)+3, column=0, columnspan=2)

    # Окно вывода
    output = tk.Text(root, height=25, width=90, wrap='word')
    output.grid(row=len(params)+4, column=0, columnspan=2)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
