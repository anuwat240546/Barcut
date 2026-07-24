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
def main():
    print("Cutting Stock Optimization")
    try:
        num_items = int(input("จำนวนรายการเหล็กที่ต้องการตัด : "))
        stock_m = float(input("ความยาวเหล็ก 1 เส้น (m.) [กด Enter เพื่อใช้ค่า 12.0 m.] : ") or 12.0)
    except ValueError:
        print("กรุณากรอกตัวเลขให้ถูกต้อง")
        return
    stock_mm = int(round(stock_m * 1000))
    groups = defaultdict(lambda: defaultdict(int))
    print("\nกรุณากรอกข้อมูลทีละรายการ")
    for i in range(num_items):
        print(f"\n[รายการที่ {i+1}]")
        size = input("ขนาดเหล็ก (เช่น RB6, DB12) : ").strip().upper()
        steel_type = input("ชนิดเหล็ก (เช่น SR24, SD40) : ").strip().upper()       
        try:
            length_m = float(input("ความยาว (m.) : "))
            quantity = int(input("จำนวนที่ต้องการ (ท่อน) : "))
        except ValueError:
            print("กรุณากรอกตัวเลขความยาวและจำนวนให้ถูกต้อง ข้ามรายการนี")
            continue            
        key = f"{size} {steel_type}"
        length_mm = int(round(length_m * 1000))
        groups[key][length_mm] += quantity
    print(" ผลการคำนวณรูปแบบการตัด")
    for key, lengths_data in groups.items():
        print(f"\n🔹 ชนิดเหล็ก: {key}")        
        lengths_mm = list(lengths_data.keys())
        demands = list(lengths_data.values())
        lengths_m = [l / 1000.0 for l in lengths_mm]
        patterns = generate_patterns(lengths_mm, stock_mm)
        if not patterns:
            print("ไม่สามารถหารูปแบบการตัดได้ (ความยาวที่ต้องการอาจมากกว่าความยาวเหล็ก 1 เส้น)")
            continue
        prob = pulp.LpProblem(f"Minimize_Stock_{key.replace(' ', '_')}", pulp.LpMinimize)
        x = [pulp.LpVariable(f"pattern_{j}", lowBound=0, cat='Integer') for j in range(len(patterns))]
        prob += pulp.lpSum(x)
        for i in range(len(lengths_mm)):
            prob += pulp.lpSum([patterns[j][i] * x[j] for j in range(len(patterns))]) >= demands[i]
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[prob.status] != 'Optimal':
            print("ไม่สามารถหาคำตอบได้")
            continue
        total_bars = 0
        for j in range(len(patterns)):
            if x[j].varValue is not None and x[j].varValue > 0:
                count = int(x[j].varValue)
                total_bars += count
                cut_details = []
                used_len_mm = 0
                for i in range(len(lengths_mm)):
                    if patterns[j][i] > 0:
                        cut_details.append(f"{lengths_m[i]}m. x {patterns[j][i]} ท่อน")
                        used_len_mm += patterns[j][i] * lengths_mm[i]
                scrap_m = (stock_mm - used_len_mm) / 1000.0
                detail_str = " | ".join(cut_details)
                print(f"   ตัดแบบที่ {j+1}: [{detail_str}] (เหลือเศษ {scrap_m:.2f} m.) => ใช้ทั้งหมด {count} เส้น")  
        print(f"   รวมใช้เหล็ก {key} ทั้งหมด : {total_bars} เส้น")
if __name__ == "__main__":
    main()