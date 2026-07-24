import streamlit as st
import pandas as pd
import pulp
from collections import defaultdict
def generate_patterns(lengths_mm, stock_mm):
    patterns = []
    def dfs(index, current_pattern, current_length):
        if index == len(lengths_mm):
            if sum(current_pattern) > 0:
                patterns.append(list(current_pattern))
            return
        max_items = (stock_mm - current_length) // lengths_mm[index]        
        for i in range(max_items, -1, -1):
            current_pattern[index] = i
            dfs(index + 1, current_pattern, current_length + i * lengths_mm[index])
            current_pattern[index] = 0
    dfs(0, [0]*len(lengths_mm), 0)
    
    maximal_patterns = []
    for p in patterns:
        used_length = sum(p[i] * lengths_mm[i] for i in range(len(lengths_mm)))
        is_maximal = True
        for i, l in enumerate(lengths_mm):
            if used_length + l <= stock_mm:
                is_maximal = False
                break
        if is_maximal:
            maximal_patterns.append(p)            
    return maximal_patterns if maximal_patterns else patterns
st.title("Cutting Stock Optimization")

col1, col2 = st.columns(2)
with col1:
    num_items = st.number_input("จำนวนรายการเหล็กที่ต้องการตัด :", min_value=1, value=1, step=1)
with col2:
    stock_m = st.number_input("ความยาวเหล็ก 1 เส้น (m.) :", min_value=1.0, value=12.0, step=0.5)

stock_mm = int(round(stock_m * 1000))

initial_data = []
for i in range(int(num_items)):
    initial_data.append({
        "ขนาดเหล็ก": "RB6", 
        "ชนิดเหล็ก": "SR24", 
        "ความยาว (m.)": 0.00, 
        "จำนวนที่ต้องการ (ท่อน)": 0
    })

df = pd.DataFrame(initial_data)

st.write("\nกรุณากรอกข้อมูลทีละรายการ")

edited_df = st.data_editor(
    df,
    column_config={
        "ขนาดเหล็ก": st.column_config.SelectboxColumn(
            "ขนาดเหล็ก",
            help="เลือกขนาดเหล็ก",
            options=["RB6", "RB9", "DB12", "DB16", "DB20", "DB25", "DB28", "DB32"],
            required=True
        ),
        "ชนิดเหล็ก": st.column_config.SelectboxColumn(
            "ชนิดเหล็ก",
            help="เลือกชนิดเหล็ก",
            options=["SR24", "SD40", "SD50"],
            required=True
        ),
        "ความยาว (m.)": st.column_config.NumberColumn(
            "ความยาว (m.)",
            min_value=0.01,
            format="%.2f"
        ),
        "จำนวนที่ต้องการ (ท่อน)": st.column_config.NumberColumn(
            "จำนวนที่ต้องการ (ท่อน)",
            min_value=0,
            step=1
        )
    },
    use_container_width=True,
    hide_index=False,
    num_rows="fixed" 
)

if st.button("เริ่มคำนวณ"):
    groups = defaultdict(lambda: defaultdict(int))
    
    for index, row in edited_df.iterrows():
        size = str(row["ขนาดเหล็ก"]).strip().upper()
        steel_type = str(row["ชนิดเหล็ก"]).strip().upper()
        length_m = float(row["ความยาว (m.)"])
        quantity = int(row["จำนวนที่ต้องการ (ท่อน)"])
        
        if length_m > 0 and quantity > 0:
            key = f"{size} {steel_type}"
            length_mm = int(round(length_m * 1000))
            groups[key][length_mm] += quantity

    st.subheader("ผลการคำนวณรูปแบบการตัด")
    
    if not groups:
        st.warning("กรุณากรอกความยาวและจำนวนที่ต้องการให้ถูกต้อง")
    else:
        all_summary_bars = []
        all_summary_scrap = []

        for key, lengths_data in groups.items():
            st.markdown(f"**🔹 ชนิดเหล็ก: {key}**")        
            lengths_mm = list(lengths_data.keys())
            demands = list(lengths_data.values())
            lengths_m = [l / 1000.0 for l in lengths_mm]
            
            with st.spinner(f'กำลังคำนวณ {key}...'):
                patterns = generate_patterns(lengths_mm, stock_mm)
                
            if not patterns:
                st.error("ไม่สามารถหารูปแบบการตัดได้ (ความยาวที่ต้องการอาจมากกว่าความยาวเหล็ก 1 เส้น)")
                continue
                
            prob = pulp.LpProblem(f"Minimize_Stock_{key.replace(' ', '_')}", pulp.LpMinimize)
            x = [pulp.LpVariable(f"pattern_{j}", lowBound=0, cat='Integer') for j in range(len(patterns))]
            prob += pulp.lpSum(x)
            
            for i in range(len(lengths_mm)):
                # ใช้ >= เพื่อไม่ให้สมการคำนวณหาทางออกไม่ได้
                prob += pulp.lpSum([patterns[j][i] * x[j] for j in range(len(patterns))]) >= demands[i]
                
            prob.solve(pulp.PULP_CBC_CMD(msg=False))
            
            if pulp.LpStatus[prob.status] != 'Optimal':
                st.error("ไม่สามารถหาคำตอบได้ (ลองตรวจสอบความยาวว่าเกิน 1 เส้นหรือไม่)")
                continue
                
            total_bars = 0
            remaining_demands = list(demands) # สำรองข้อมูลความต้องการจริงไว้หักลบ
            actual_bars = []
            for j in range(len(patterns)):
                if x[j].varValue is not None and x[j].varValue > 0:
                    count = int(x[j].varValue)
                    total_bars += count
                    
                    # จำลองการตัดเหล็กทีละเส้น
                    for _ in range(count):
                        bar_cuts = []
                        used_len_mm = 0
                        for i in range(len(lengths_mm)):
                            if patterns[j][i] > 0:
                                # เอาเท่าที่ Pattern ระบุ หรือเท่าที่ "ยังขาดอยู่" (อันไหนน้อยกว่า เอาอันนั้น)
                                pieces_to_take = min(patterns[j][i], remaining_demands[i])
                                
                                if pieces_to_take > 0:
                                    bar_cuts.append(f"{lengths_m[i]}m. x {pieces_to_take} ท่อน")
                                    used_len_mm += pieces_to_take * lengths_mm[i]
                                    remaining_demands[i] -= pieces_to_take # หักยอดความต้องการออก
                        
                        scrap_m = (stock_mm - used_len_mm) / 1000.0
                        detail_str = " | ".join(bar_cuts) if bar_cuts else "ไม่ได้ใช้"
                        
                        actual_bars.append({
                            "detail": detail_str,
                            "scrap": scrap_m
                        })
            summary_dict = defaultdict(int)
            for b in actual_bars:
                # ถ้าเส้นไหนไม่ได้ตัดเลย (แปลว่าโปรแกรมซื้อเผื่อมาให้ฟรีๆ) เราจะไม่นับ
                if b["detail"] != "ไม่ได้ใช้":
                    summary_dict[(b["detail"], b["scrap"])] += 1
                else:
                    total_bars -= 1 # คืนเหล็ก 1 เส้นกลับสโตร์
            idx = 1
            for (detail_str, scrap_m), count in summary_dict.items():
                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;ตัดแบบที่ {idx}: [{detail_str}] (เหลือเศษ {scrap_m:.2f} m.) => ใช้ทั้งหมด {count} เส้น")  
                idx += 1
                
                # เก็บข้อมูลเศษ
                if scrap_m > 0:
                    all_summary_scrap.append({
                        "ชนิดเหล็ก": key,
                        "ความยาวเศษ (m.)": f"{scrap_m:.2f}",
                        "จำนวน (ท่อน)": count
                    })
            
            st.write(f"**&nbsp;&nbsp;&nbsp;&nbsp;รวมใช้เหล็ก {key} ทั้งหมด : {total_bars} เส้น**")
            st.divider()
            
            all_summary_bars.append({
                "ชนิดเหล็ก": key,
                "จำนวนที่ต้องใช้ (เส้น)": total_bars
            })
        if all_summary_bars:
            st.markdown("---")
            st.header("📋 สรุปภาพรวมทั้งหมด")
            col_sum1, col_sum2 = st.columns(2)
            
            with col_sum1:
                st.subheader("🛒 สรุปจำนวนเหล็กที่ต้องสั่งซื้อ")
                st.dataframe(pd.DataFrame(all_summary_bars), use_container_width=True, hide_index=True)
                
            with col_sum2:
                st.subheader("♻️ สรุปเศษเหล็กที่เหลือ")
                if all_summary_scrap:
                    df_scrap = pd.DataFrame(all_summary_scrap)
                    df_scrap_grouped = df_scrap.groupby(["ชนิดเหล็ก", "ความยาวเศษ (m.)"], as_index=False)["จำนวน (ท่อน)"].sum()
                    st.dataframe(df_scrap_grouped, use_container_width=True, hide_index=True)
                else:
                    st.success("ไม่มีเศษเหล็กเหลือทิ้งเลย")