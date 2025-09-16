import streamlit as st

# 計算函數
def calc_total(A, B, C, E, G):
    service_fee = 0.15   # 代購服務費
    tax = 0.05           # 營業稅

    D = B * C          # 商品價格
    H = B * G          # 商品總重量

    # 國際運費單價判斷
    if H <= 1:
        unit_freight = 30
    elif H <= 4:
        unit_freight = 25
    elif H <= 7:
        unit_freight = 19
    elif H <= 10:
        unit_freight = 17
    else:
        unit_freight = 15

    F = H * unit_freight  # 國際運費
    total = (D + E + F) * A * (1 + service_fee) * (1 + tax)
    return total, D, F, H

# Streamlit UI
st.title("🛒 淘寶代購試算器")

A = st.number_input("匯率 A", value=4.4, step=0.1)
B = st.number_input("數量 B", value=1000, step=1)
C = st.number_input("商品單價 C (RMB)", value=4.8, step=0.1)
E = st.number_input("境內運費 E (RMB)", value=0.0, step=0.1)
G = st.number_input("單個商品重量 G (kg)", value=0.14, step=0.01)

if st.button("計算"):
    total, D, F, H = calc_total(A, B, C, E, G)
    st.success(f"📦 商品價格 D = {D} RMB")
    st.success(f"⚖️ 總重量 H = {H} kg")
    st.success(f"🚚 國際運費 F = {F} RMB")
    st.info(f"✅ 代購總金額：約 {round(total, 2)} 元")
