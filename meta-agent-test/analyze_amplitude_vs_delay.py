#!/usr/bin/env python3
"""验证电机响应时间对target量级的依赖性"""
import csv
import math
from collections import defaultdict

with open('test_logs/data_csv/t27_joint_20260518_1_real.csv') as f:
    rows = list(csv.DictReader(f))

ts = [int(r['timestamp_ns']) for r in rows]
fs = 1e9 / (ts[1] - ts[0])

# 分析几个代表性关节
joints = [
    'right_hip_pitch_joint',  # 大范围运动
    'left_hip_roll_joint',    # 限幅饱和
    'right_hip_roll_joint',   # 几乎不跟随
    'left_knee_pitch_joint',  # 中等范围
    'right_ankle_pitch_joint',# 并行关节
]

print(f"{'关节名':>30} {'量级区间':>10} {'帧数':>5} {'平均target变化':>12} {'平均跟踪误差':>12} {'零滞相关':>8}")
print('-' * 85)

for joint in joints:
    target = [float(r[f'pos_des_lpf_{joint}']) for r in rows]
    pos    = [float(r[f'pos_{joint}']) for r in rows]
    n = min(len(target), len(pos))
    
    # 计算每步的 target 变化量 (delta)
    deltas = [abs(target[i+1] - target[i]) for i in range(n-1)]
    errors = [abs(target[i] - pos[i]) for i in range(n)]
    
    # 按 delta 量级分桶
    buckets = [(0, 0.01), (0.01, 0.05), (0.05, 0.1), (0.1, 0.5), (0.5, float('inf'))]
    for lo, hi in buckets:
        indices = [i for i, d in enumerate(deltas) if lo <= d < hi]
        if len(indices) < 5:
            continue
        
        # 该桶内的平均误差
        mean_err = sum(errors[i] for i in indices) / len(indices)
        
        # 该桶内的零滞相关 (target vs pos at same time)
        xs = [target[i] for i in indices[:min(len(indices), 500)]]
        ys = [pos[i] for i in indices[:min(len(indices), 500)]]
        if len(xs) > 5:
            mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
            vx = [v-mx for v in xs]; vy = [v-my for v in ys]
            den = math.sqrt(sum(v*v for v in vx)*sum(v*v for v in vy))
            c = sum(a*b for a,b in zip(vx,vy))/den if den>1e-12 else 0
        else:
            c = 0
        
        label = f'[{lo:4.2f}, {hi:4.2f})'
        mean_delta = sum(deltas[i] for i in indices)/len(indices) if indices else 0
        print(f"{joint:>30} {label:>10} {len(indices):>5} {mean_delta:>12.4f} {mean_err:>12.4f} {c:>8.3f}")

print()
print("=" * 85)

# 更直观: 把每个关节的数据分成"小动作"和"大动作"两半
print(f"\n{'关节名':>30} {'小动作误差':>10} {'大动作误差':>10} {'小/大比值':>10} {'小动作占比':>10}")
print('-' * 75)

for joint in joints:
    target = [float(r[f'pos_des_lpf_{joint}']) for r in rows]
    pos    = [float(r[f'pos_{joint}']) for r in rows]
    n = min(len(target), len(pos))
    
    deltas = [abs(target[i+1] - target[i]) for i in range(n-1)]
    errors = [abs(target[i] - pos[i]) for i in range(n)]
    
    median_delta = sorted(deltas)[len(deltas)//2]
    
    small = [i for i, d in enumerate(deltas) if d < median_delta]
    large = [i for i, d in enumerate(deltas) if d >= median_delta]
    
    small_err = sum(errors[i] for i in small) / len(small) if small else 0
    large_err = sum(errors[i] for i in large) / len(large) if large else 0
    
    ratio = small_err / large_err if large_err > 1e-6 else float('inf')
    small_pct = len(small) / n * 100
    
    print(f"{joint:>30} {small_err:>10.4f} {large_err:>10.4f} {ratio:>10.2f}x {small_pct:>9.1f}%")
