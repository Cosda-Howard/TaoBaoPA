import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="淘寶代購試算器（多商品）", layout="wide")

st.title("🛒 淘寶代購試算器（多商品・動態新增）")

# ------- Sidebar：共用參數 -------
with st.sidebar:
    st.header("共用參數")
    A = st.number_input("匯率 A", value=4.4, step=0.1, min_value=0.0)
    service_fee = st.number_input("代購服務費（%）", value=15.0, step=0.5, min_value=0.0) / 100.0
    tax = st.number_input("營業稅（%）", value=5.0, step=0.5, min_value=0.0) / 100.0
    rounding = st.selectbox("金額四捨五入位數", [0, 1, 2], index=0,
                            help="0=到個位，1=到小數1位，2=到小數2位")

    st.markdown("---")
    st.caption("✳ 國際運費單價（人民幣 / kg）")
    st.write("1kg 以下：30｜2–4kg：25｜5–7kg：19｜8–10kg：17｜11kg 以上：15")

# ------- 初始化資料表 -------
DEFAULT_ROWS = [
    {"品名": "", "數量B": 1, "單價C(RMB)": 0.0, "境內運費E(RMB)": 0.0, "單件重量G(kg)": 0.0}
]
if "items_df" not in st.session_state:
    st.session_state.items_df = pd.DataFrame(DEFAULT_ROWS)

def _to_df(val):
    if isinstance(val, pd.DataFrame):
        return val.copy()
    elif isinstance(val, list):
        return pd.DataFrame(val)
    elif isinstance(val, dict):
        return pd.DataFrame.from_dict(val)
    else:
        return pd.DataFrame(DEFAULT_ROWS)

st.subheader("① 輸入商品資料（可直接新增/刪除列）")

# ✅ 用 form 包住，避免每次格子提交就 rerun
with st.form("items_form", clear_on_submit=False):
    edited_value = st.data_editor(
        st.session_state.items_df,
        key="items_editor",
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "品名": st.column_config.TextColumn("品名"),
            "數量B": st.column_config.NumberColumn("數量B", min_value=0, step=1),         # 整數
            "單價C(RMB)": st.column_config.NumberColumn("單價C (RMB)", min_value=0.0, step=0.01, format="%.2f"),
            "境內運費E(RMB)": st.column_config.NumberColumn("境內運費 E (RMB)", min_value=0.0, step=0.01, format="%.2f"),
            "單件重量G(kg)": st.column_config.NumberColumn("單件重量 G (kg)", min_value=0.0, step=0.01, format="%.2f"),
        },
        hide_index=True,
    )
    submitted = st.form_submit_button("✅ 更新資料")

# 只有按下「更新資料」時才把改動寫回狀態
if submitted:
    st.session_state.items_df = _to_df(edited_value)

# 下游計算都用這個 df（不會再出現第一次跳掉）
items_df = st.session_state.items_df

# ------- 計算函數 -------
def freight_unit_by_weight(total_weight_kg: float) -> float:
    """依商品總重量 H 判斷每公斤運費單價（人民幣）"""
    if total_weight_kg <= 1:
        return 30
    elif total_weight_kg <= 4:
        return 25
    elif total_weight_kg <= 7:
        return 19
    elif total_weight_kg <= 10:
        return 17
    else:
        return 15

def calc_row(row):
    B = row.get("數量B", 0) or 0
    C = row.get("單價C(RMB)", 0.0) or 0.0
    E = row.get("境內運費E(RMB)", 0.0) or 0.0
    G = row.get("單件重量G(kg)", 0.0) or 0.0

    # 商品價格 D、商品總重量 H
    D = B * C
    H = B * G

    # 國際運費
    unit = freight_unit_by_weight(H)
    F = H * unit

    # 單項總金額（換匯 + 服務費 + 稅）
    total_item = (D + E + F) * A * (1 + service_fee) * (1 + tax)

    return {
        "品名": row.get("品名", ""),
        "數量B": B,
        "單價C(RMB)": C,
        "境內運費E(RMB)": E,
        "單件重量G(kg)": G,
        "商品價格D(RMB)": D,
        "總重量H(kg)": H,
        "國際運費單價(RMB/kg)": unit,
        "國際運費F(RMB)": F,
        "單項金額(含稅/換匯)": total_item,
    }

# ======= 計算區（請整段取代原本的計算程式）=======
if st.button("計算", type="primary"):
    # 1) 取用最新資料（form 提交後寫在 session_state）
    df = st.session_state.items_df.copy()

    if df.empty:
        st.warning("目前沒有可計算的資料，請先在上方表格輸入並按「✅ 更新資料」。")
    else:
        # 2) 數值欄位轉型並補 NaN
        num_cols = ["數量B", "單價C(RMB)", "境內運費E(RMB)", "單件重量G(kg)"]
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        # 3) 移除全 0 的空白列
        mask_empty = (
            (df["數量B"] == 0)
            & (df["單價C(RMB)"] == 0)
            & (df["境內運費E(RMB)"] == 0)
            & (df["單件重量G(kg)"] == 0)
        )
        df = df[~mask_empty]

        if df.empty:
            st.warning("沒有有效的商品列可計算，請輸入數量/單價等資料後再試。")
        else:
            # 4) 逐列計算
            results = []
            for _, row in df.iterrows():
                B = float(row["數量B"])
                C = float(row["單價C(RMB)"])
                E = float(row["境內運費E(RMB)"])
                G = float(row["單件重量G(kg)"])

                D = B * C                   # 商品價格
                H = B * G                   # 總重量
                unit = freight_unit_by_weight(H)
                F = H * unit                # 國際運費（人民幣）

                total_item = (D + E + F) * A * (1 + service_fee) * (1 + tax)

                results.append({
                    "品名": row.get("品名", ""),
                    "數量B": B,
                    "單價C(RMB)": C,
                    "境內運費E(RMB)": E,
                    "單件重量G(kg)": G,
                    "商品價格D(RMB)": D,
                    "總重量H(kg)": H,
                    "國際運費單價(RMB/kg)": unit,
                    "國際運費F(RMB)": F,
                    "單項金額(含稅/換匯)": total_item,
                })

            # 5) 顯示結果（只格式化顯示，不改變數值）
            result_df = pd.DataFrame(results)

            st.subheader("② 計算明細")
            st.dataframe(
                result_df,
                use_container_width=True,
                column_config={
                    "單價C(RMB)": st.column_config.NumberColumn("單價C(RMB)", format="%.2f"),
                    "境內運費E(RMB)": st.column_config.NumberColumn("境內運費E(RMB)", format="%.2f"),
                    "單件重量G(kg)": st.column_config.NumberColumn("單件重量G(kg)", format="%.2f"),
                    "商品價格D(RMB)": st.column_config.NumberColumn("商品價格D(RMB)", format="%.2f"),
                    "總重量H(kg)": st.column_config.NumberColumn("總重量H(kg)", format="%.2f"),
                    "國際運費F(RMB)": st.column_config.NumberColumn("國際運費F(RMB)", format="%.2f"),
                    "單項金額(含稅/換匯)": st.column_config.NumberColumn("單項金額(含稅/換匯)", format="%.2f"),
                },
            )

            total_sum = float(result_df["單項金額(含稅/換匯)"].sum())
            st.success(f"✅ 全部商品代購總金額：約 {total_sum:,.2f} 元")

            total_weight = float(result_df["總重量H(kg)"].sum())
            st.caption(f"總重量（所有商品加總）：{total_weight:.2f} kg")
# ======= 計算區結束 =======







