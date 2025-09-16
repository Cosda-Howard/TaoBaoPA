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
            "數量B": st.column_config.NumberColumn("數量B", min_value=0, step=1),
            "單價C(RMB)": st.column_config.NumberColumn("單價C (RMB)", min_value=0.0, step=0.1),
            "境內運費E(RMB)": st.column_config.NumberColumn("境內運費 E (RMB)", min_value=0.0, step=0.1),
            "單件重量G(kg)": st.column_config.NumberColumn("單件重量 G (kg)", min_value=0.0, step=0.01),
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

# ------- 計算所有列 -------
if st.button("計算", type="primary"):
    # 過濾掉空白列（數量與單價皆為 0 視為空白）
    filtered = edited_df.fillna(0)
    filtered = filtered[~((filtered["數量B"] == 0) & (filtered["單價C(RMB)"] == 0) &
                          (filtered["境內運費E(RMB)"] == 0) & (filtered["單件重量G(kg)"] == 0))]

    results = [calc_row(r) for r in filtered.to_dict(orient="records")]
    if results:
        result_df = pd.DataFrame(results)

        # 四捨五入顯示
        q = int(rounding)
        cols_round = [
            "單價C(RMB)", "境內運費E(RMB)", "單件重量G(kg)",
            "商品價格D(RMB)", "總重量H(kg)", "國際運費F(RMB)",
            "單項金額(含稅/換匯)"
        ]
        for c in cols_round:
            result_df[c] = result_df[c].apply(lambda x: round(float(x), q))

        st.subheader("② 計算明細")
        st.dataframe(result_df, use_container_width=True)

        total_sum = float(result_df["單項金額(含稅/換匯)"].sum())
        st.success(f"✅ 全部商品代購總金額：約 {round(total_sum, q)} 元")

        # 小結資訊
        total_weight = float(result_df["總重量H(kg)"].sum())
        st.caption(f"總重量（所有商品加總）：{round(total_weight, 2)} kg")
    else:
        st.warning("請先輸入至少一筆有效商品資料（數量與單價不可全部為 0）。")

st.caption("提示：下表可直接按右下角 + 來新增列；也可刪除列、編輯數字。")




