import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# ----------------------
# ボイド率計算関数
def calc_void_fraction(level):
    return (1200 - level) / 1200

# 不確かさ計算（95%信頼区間の割合）
def calc_uncertainty(data):
    n = len(data)
    if n == 0:
        return 0, 0, 0, 0
    elif n == 1:
        mean = data[0]
        return mean, mean, mean, 0
    arr = np.array(data)
    mean = arr.mean()
    std_err = arr.std(ddof=1) / np.sqrt(n)
    conf_interval = 1.96 * std_err  # 95%信頼区間
    lower = mean - conf_interval
    upper = mean + conf_interval
    relative_uncertainty = (upper - lower) / mean * 100 if mean != 0 else 0
    return mean, lower, upper, relative_uncertainty

# PNGグラフ保存用関数
def fig_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf

# 一枚戻る関数
def go_back():
    if st.session_state.step > 1:
        st.session_state.step -= 1

# ----------------------
# セッションステート初期化
if 'step' not in st.session_state:
    st.session_state.step = 1

if 'JG' not in st.session_state:
    st.session_state.JG = 0.0
if 'JL' not in st.session_state:
    st.session_state.JL = 0.0

if 'measurements' not in st.session_state:
    st.session_state.measurements = []

if 'confirm_end' not in st.session_state:
    st.session_state.confirm_end = False

# ----------------------
# ステップごとの画面処理

# ステップ1: JG, JL 入力画面
if st.session_state.step == 1:
    st.title("測定を始める (JG, JL入力)")
    JG = st.number_input("JGの値 (m/s)", min_value=0.0, format="%.1f", value=st.session_state.JG)
    JL = st.number_input("JLの値 (m/s)", min_value=0.0, format="%.2f", value=st.session_state.JL)

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("決定"):
            st.session_state.JG = JG
            st.session_state.JL = JL
            st.session_state.measurements = []
            st.session_state.confirm_end = False
            st.session_state.step = 2
    with col2:
        if st.button("一枚戻る"):
            # 1ページ目なので戻れない、無視
            st.warning("これ以上戻れません。")

# ステップ2: 液位入力画面
elif st.session_state.step == 2:
    st.title(f"測定{len(st.session_state.measurements)+1}回目：液位入力")
    liquid_level = st.number_input("液位 (mm)", min_value=0.0, max_value=1200.0, format="%.0f")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("決定"):
            if liquid_level is not None and liquid_level > 0:
                st.session_state.measurements.append(liquid_level)
                st.session_state.step = 3

            else:
                st.warning("液位を0より大きい値で入力してください。")
    with col2:
        if st.button("一枚戻る"):
            go_back()

# ステップ3: 結果表示＋グラフ＋分岐制御
elif st.session_state.step == 3:
    n = len(st.session_state.measurements)
    voids = [calc_void_fraction(lv) for lv in st.session_state.measurements]
    mean, lower, upper, uncertainty = calc_uncertainty(voids)

    st.title(f"測定{n}回目 結果")
    st.write(f"液位: {st.session_state.measurements[-1]:.2f} mm")
    st.write(f"今回のボイド率: {voids[-1]:.4f}")
    st.write(f"ボイド率算術平均値: {mean:.4f}")
    st.write(f"95%信頼区間: {lower:.4f} ~ {upper:.4f}")
    st.write(f"不確かさ: {uncertainty:.2f} %")
    st.write(f"測定回数: {n}回")

    # グラフ作成
    x = list(range(1, n+1))
    cumulative_means = [np.mean(voids[:i]) for i in range(1, n+1)]
    cumulative_means = np.array(cumulative_means)

    fig, ax = plt.subplots()
    ax.plot(x, voids, marker='o', markerfacecolor='r', markeredgecolor='r',linestyle='none', label='Each α')
    ax.plot(x, cumulative_means, marker='x', markerfacecolor='green',markeredgecolor='g', linestyle='none', label='Cumulative Mean α')

    # 最新の累積平均値 ±1%の水平線
    last_mean = cumulative_means[-1]
    ax.hlines(last_mean * 0.99, xmin=0, xmax=110, colors='blue', linestyles='-', label='Cumulative Mean α ×0.99')
    ax.hlines(last_mean * 1.01, xmin=0, xmax=110, colors='blue', linestyles='--', label='Cumulative Mean α ×1.01')

    ax.set_xlabel('Count')
    ax.set_ylabel('α')
    ax.legend(frameon=False)
    ax.grid(True)
    if n <= 50:
        ax.set_xlim(0, 50)
    else:
        ax.set_xlim(0, ((n // 10) + 1) * 10)

    st.pyplot(fig)

    # 一枚戻るボタン
    if st.button("戻る"):
        go_back()

    # 10回ごとの判定（10,20,30,...）
    if n % 10 == 0:
        if not st.session_state.confirm_end:
            st.warning(f"{n}回の測定が終了しました。測定をやめますか？")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("やめる"):
                    st.session_state.confirm_end = True

            with col2:
                if st.button("続ける"):
                    st.session_state.step = 2

        else:
            # 測定終了処理画面
            st.success("測定終了処理")

            # 最終的な95%信頼区間・標準誤差・不確かさを計算
            arr = np.array(voids)
            mean = arr.mean()
            std_err = arr.std(ddof=1) / np.sqrt(len(arr)) if len(arr) > 1 else 0
            conf_interval = 1.96 * std_err if len(arr) > 1 else 0
            lower = mean - conf_interval
            upper = mean + conf_interval
            uncertainty = (upper - lower) / mean * 100 if mean != 0 else 0
            conf_interval_str = f"{lower:.4f} ~ {upper:.4f}"

            # 全行に同じ値を入れるリストを作成
            conf_intervals = [conf_interval_str] * n
            std_errs = [std_err] * n
            uncertainties = [uncertainty] * n
            means_list = [mean] * n

            # CSVデータ作成
            df = pd.DataFrame({
                '測定回数': range(1, n+1),
                '液位[mm]': st.session_state.measurements,
                'ボイド率': voids,
                '平均': means_list,
                '95%信頼区間': conf_intervals,
                '標準誤差': std_errs,
                '不確かさ[%]': uncertainties,
            })
            csv = df.to_csv(index=False).encode('utf-8-sig')

            # ファイル名作成
            jg_str = f"{st.session_state.JG:.1f}".replace('.', '')
            jl_str = f"{st.session_state.JL:.2f}".replace('.', '')
            csv_file_name = f"void_JG{jg_str}JL{jl_str}.csv"
            png_file_name = f"void_JG{jg_str}JL{jl_str}.png"

            st.download_button("CSVをダウンロード", data=csv, file_name=csv_file_name, mime='text/csv')

            # グラフダウンロード
            png_buf = fig_to_png_bytes(fig)
            st.download_button("グラフをPNGでダウンロード", data=png_buf, file_name=png_file_name, mime='image/png')

            st.write("測定を本当に終了しますか？")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("はい"):
                    # セッションリセットしてstep=1に戻る
                    st.session_state.step = 1
                    st.session_state.measurements = []
                    st.session_state.confirm_end = False

            with col2:
                if st.button("いいえ"):
                    # 液位入力画面に戻る
                    st.session_state.step = 2
                    st.session_state.confirm_end = False

    else:
        # 10回の倍数でなければ通常進行
        if st.button("次の測定に進む"):
            st.session_state.step = 2

           
