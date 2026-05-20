#!/usr/bin/env python3
"""演示 hip/knee 执行链延迟的计算方法"""
import csv
import math

# 读取数据
with open('test_logs/data_csv/t27_joint_20260518_1_real.csv') as f:
    rows = list(csv.DictReader(f))

ts = [int(r['timestamp_ns']) for r in rows]
fs = 1e9 / (ts[1] - ts[0])
print(f'采样率: {fs:.1f} Hz  (即每样本间隔 {1000/fs:.2f} ms)')
print()

# 选一个代表性关节
joint = 'right_hip_pitch_joint'
target = [float(r[f'pos_des_lpf_{joint}']) for r in rows]
pos    = [float(r[f'pos_{joint}']) for r in rows]
n = min(len(target), len(pos))

print(f'=== {joint} ===')
print(f'数据长度: {n} 帧')

# 对每个 lag 扫描
best_lag, best_corr = 0, -2.0
results = []
for lag in range(-25, 26):
    xs, ys = [], []
    for i in range(n):
        j = i + lag
        if 0 <= j < n:
            xs.append(target[i])
            ys.append(pos[j])
    if len(xs) < 10: 
        continue
    mx = sum(xs)/len(xs)
    my = sum(ys)/len(ys)
    vx = [v-mx for v in xs]
    vy = [v-my for v in ys]
    den = math.sqrt(sum(v*v for v in vx) * sum(v*v for v in vy))
    c = sum(a*b for a,b in zip(vx,vy))/den if den>1e-12 else -2
    lag_ms = lag/fs*1000
    results.append((lag, lag_ms, c))
    if c > best_corr:
        best_corr = c
        best_lag = lag

print(f'\n核心计算: 把 pos 信号整体平移 lag 个样本, 算与 target 的 Pearson 相关系数')
print(f'{"lag(样本)":>10} {"lag(ms)":>8} {"相关性":>8}  {"说明":>20}')
print('-' * 50)
for lag, lag_ms, c in results:
    marker = ''
    if lag == 0: marker = '(零滞, 即实时)'
    if lag == best_lag: marker = f'◄ 最佳! pos滞后{lag_ms:.0f}ms'
    if lag in [-13, -10, -5, 0, 5, 10, 13, best_lag]:
        print(f'{lag:>10} {lag_ms:>8.1f} {c:>8.3f}  {marker}')

print(f'\n结论:')
print(f'  pos 向后平移 {best_lag} 个样本时, 与 target 最相似 (r={best_corr:.3f})')
print(f'  延迟 = {best_lag} 样本 × {1000/fs:.2f} ms/样本 = {best_lag/fs*1000:.1f} ms')
print(f'  含义: 实际关节位置 {best_lag/fs*1000:.0f}ms 前的位置 ≈ 当前 target')
print()

# 对比几个关节的延迟可靠性
print(f'{"关节名":>35} {"延迟(ms)":>10} {"最佳相关":>8} {"可靠性":>8}')
print('-' * 65)
for joint in ['right_hip_pitch_joint', 'left_hip_pitch_joint', 
              'left_hip_roll_joint', 'right_hip_roll_joint',
              'left_knee_pitch_joint', 'right_knee_pitch_joint',
              'left_ankle_roll_joint', 'right_ankle_pitch_joint']:
    target = [float(r[f'pos_des_lpf_{joint}']) for r in rows]
    pos    = [float(r[f'pos_{joint}']) for r in rows]
    
    best_l, best_c = 0, -2.0
    for lag in range(-25, 26):
        xs, ys = [], []
        for i in range(len(target)):
            j = i + lag
            if 0 <= j < min(len(target), len(pos)):
                xs.append(target[i])
                ys.append(pos[j])
        if len(xs) < 10: continue
        mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
        vx = [v-mx for v in xs]; vy = [v-my for v in ys]
        den = math.sqrt(sum(v*v for v in vx)*sum(v*v for v in vy))
        c = sum(a*b for a,b in zip(vx,vy))/den if den>1e-12 else -2
        if c > best_c: best_c = c; best_l = lag
    
    reliable = '✓' if abs(best_c) > 0.3 else '⚠ 弱相关' if abs(best_c) > 0.1 else '✗ 不可靠'
    print(f'{joint:>35} {best_l/fs*1000:>10.1f} {best_c:>8.3f} {reliable:>8}')
