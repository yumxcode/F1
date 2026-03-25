#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T1 静态测试数据分析脚本
用于分析 T1-1（零位偏差）、T1-2（IMU稳定性）、T1-3（关节速度噪声）测试数据
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class T1Analyzer:
    def __init__(self, csv_file):
        self.csv_file = Path(csv_file)
        if not self.csv_file.exists():
            raise FileNotFoundError(f"文件不存在: {csv_file}")
        print(f"正在读取文件: {self.csv_file}")
        self.df = pd.read_csv(csv_file, comment='#')
        self.init_state = self._read_init_state()
        self.joint_names = [col.replace('pos_', '') for col in self.df.columns if col.startswith('pos_')]
        print(f"数据行数: {len(self.df)}, 关节数量: {len(self.joint_names)}")
        print(f"采样时长: {(self.df['timestamp_ns'].iloc[-1] - self.df['timestamp_ns'].iloc[0]) / 1e9:.2f} 秒")

    def _read_init_state(self):
        init_state = {}
        with open(self.csv_file, 'r') as f:
            for line in f:
                if line.startswith('# init_state'):
                    values = line.strip().split(',')[1:]
                    idx = 0
                    for col in self.df.columns:
                        if col.startswith('pos_'):
                            joint_name = col.replace('pos_', '')
                            init_state[joint_name] = float(values[idx])
                        idx += 1
                    break
        return init_state

    def analyze_t1_1_zero_offset(self):
        """T1-1: 零位偏差分析"""
        print("\n" + "="*60)
        print("T1-1: 零位偏差分析")
        print("="*60)
        results = []
        for joint in self.joint_names:
            pos_col = f'pos_{joint}'
            init_pos = self.init_state.get(joint, 0.0)
            offset_mean = self.df[pos_col].mean() - init_pos
            offset_std = self.df[pos_col].std()
            offset_max = (self.df[pos_col] - init_pos).abs().max()
            results.append({'joint': joint, 'init_pos': init_pos, 'mean_pos': self.df[pos_col].mean(),
                           'offset_mean': offset_mean, 'offset_std': offset_std, 'offset_max': offset_max})
            threshold = 0.02
            status = "✓ 通过" if abs(offset_mean) < threshold else "✗ 超标"
            print(f"{joint:20s}: 偏差均值={offset_mean:+.4f} rad ({offset_mean*57.3:+.2f}°), "
                  f"标准差={offset_std:.4f} rad, 最大偏差={offset_max:.4f} rad  {status}")
        return pd.DataFrame(results)

    def analyze_t1_2_imu_stability(self):
        """T1-2: IMU 稳定性分析"""
        print("\n" + "="*60)
        print("T1-2: IMU 稳定性分析")
        print("="*60)
        print("\n角速度稳定性:")
        for col in ['ang_vel_x', 'ang_vel_y', 'ang_vel_z']:
            mean_val = self.df[col].mean()
            std_val = self.df[col].std()
            max_val = self.df[col].abs().max()
            status = "✓ 通过" if abs(mean_val) < 0.005 and std_val < 0.01 else "✗ 超标"
            print(f"{col:12s}: 均值={mean_val:+.6f} rad/s, 标准差={std_val:.6f} rad/s, "
                  f"最大值={max_val:.6f} rad/s  {status}")
        print("\n欧拉角稳定性:")
        for col, name in zip(['euler_x', 'euler_y', 'euler_z'], ['Roll', 'Pitch', 'Yaw']):
            mean_val = self.df[col].mean()
            std_val = self.df[col].std()
            if name in ['Roll', 'Pitch']:
                status = "✓ 通过" if abs(mean_val) < 0.01 and std_val < 0.005 else "✗ 超标"
            else:
                status = "✓ 通过" if std_val < 0.005 else "✗ 超标"
            print(f"{name:6s} ({col}): 均值={mean_val:+.6f} rad ({mean_val*57.3:+.2f}°), "
                  f"标准差={std_val:.6f} rad  {status}")

    def analyze_t1_3_joint_velocity_noise(self):
        """T1-3: 关节速度噪声分析"""
        print("\n" + "="*60)
        print("T1-3: 关节速度噪声分析")
        print("="*60)
        results = []
        for joint in self.joint_names:
            vel_col = f'vel_{joint}'
            mean_val = self.df[vel_col].mean()
            std_val = self.df[vel_col].std()
            sigma_3_range = 3 * std_val
            results.append({'joint': joint, 'mean_vel': mean_val, 'std_vel': std_val, '3sigma_range': sigma_3_range})
            threshold = 0.1
            status = "✓ 通过" if sigma_3_range < threshold else "✗ 超标"
            print(f"{joint:20s}: 均值={mean_val:+.6f} rad/s, 标准差={std_val:.6f} rad/s, "
                  f"3σ范围={sigma_3_range:.6f} rad/s  {status}")
        return pd.DataFrame(results)

    def plot_results(self, output_dir=None):
        if output_dir is None:
            output_dir = self.csv_file.parent
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        time_s = (self.df['timestamp_ns'] - self.df['timestamp_ns'].iloc[0]) / 1e9

        # 图1: 关节位置偏差
        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        axes = axes.flatten()
        for idx, joint in enumerate(self.joint_names[:12]):
            pos_col = f'pos_{joint}'
            init_pos = self.init_state.get(joint, 0.0)
            offset = (self.df[pos_col] - init_pos) * 57.3
            axes[idx].plot(time_s, offset, linewidth=0.5)
            axes[idx].axhline(y=0, color='r', linestyle='--', linewidth=1)
            axes[idx].set_title(f'{joint}')
            axes[idx].set_xlabel('Time (s)')
            axes[idx].set_ylabel('Offset (deg)')
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't1_1_joint_offset.png', dpi=150)
        print(f"\n已保存图表: {output_dir / 't1_1_joint_offset.png'}")
        plt.close()

        # 图2: IMU 角速度
        fig, axes = plt.subplots(3, 1, figsize=(12, 8))
        for idx, (col, name) in enumerate(zip(['ang_vel_x', 'ang_vel_y', 'ang_vel_z'], ['ω_x', 'ω_y', 'ω_z'])):
            axes[idx].plot(time_s, self.df[col], linewidth=0.5)
            axes[idx].axhline(y=0, color='r', linestyle='--', linewidth=1)
            axes[idx].set_title(f'Angular Velocity {name}')
            axes[idx].set_xlabel('Time (s)')
            axes[idx].set_ylabel('rad/s')
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't1_2_imu_angular_velocity.png', dpi=150)
        print(f"已保存图表: {output_dir / 't1_2_imu_angular_velocity.png'}")
        plt.close()

        # 图3: IMU 欧拉角
        fig, axes = plt.subplots(3, 1, figsize=(12, 8))
        for idx, (col, name) in enumerate(zip(['euler_x', 'euler_y', 'euler_z'], ['Roll', 'Pitch', 'Yaw'])):
            axes[idx].plot(time_s, self.df[col] * 57.3, linewidth=0.5)
            axes[idx].axhline(y=0, color='r', linestyle='--', linewidth=1)
            axes[idx].set_title(f'{name}')
            axes[idx].set_xlabel('Time (s)')
            axes[idx].set_ylabel('deg')
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't1_2_imu_euler_angles.png', dpi=150)
        print(f"已保存图表: {output_dir / 't1_2_imu_euler_angles.png'}")
        plt.close()

        # 图4: 关节速度噪声
        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        axes = axes.flatten()
        for idx, joint in enumerate(self.joint_names[:12]):
            vel_col = f'vel_{joint}'
            axes[idx].plot(time_s, self.df[vel_col], linewidth=0.5, alpha=0.7)
            axes[idx].axhline(y=0, color='r', linestyle='--', linewidth=1)
            std_val = self.df[vel_col].std()
            axes[idx].axhline(y=3*std_val, color='orange', linestyle=':', linewidth=1, label='±3σ')
            axes[idx].axhline(y=-3*std_val, color='orange', linestyle=':', linewidth=1)
            axes[idx].set_title(f'{joint}')
            axes[idx].set_xlabel('Time (s)')
            axes[idx].set_ylabel('Velocity (rad/s)')
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't1_3_joint_velocity_noise.png', dpi=150)
        print(f"已保存图表: {output_dir / 't1_3_joint_velocity_noise.png'}")
        plt.close()

    def generate_report(self, output_file=None):
        if output_file is None:
            output_file = self.csv_file.parent / f"{self.csv_file.stem}_report.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\nT1 静态测试分析报告\n" + "="*60 + "\n")
            f.write(f"数据文件: {self.csv_file}\n")
            f.write(f"数据行数: {len(self.df)}\n")
            f.write(f"采样时长: {(self.df['timestamp_ns'].iloc[-1] - self.df['timestamp_ns'].iloc[0]) / 1e9:.2f} 秒\n\n")
            df_offset = self.analyze_t1_1_zero_offset()
            f.write(df_offset.to_string(index=False) + "\n\n")
            self.analyze_t1_2_imu_stability()
            df_vel = self.analyze_t1_3_joint_velocity_noise()
            f.write(df_vel.to_string(index=False) + "\n")
        print(f"\n已保存报告: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='T1 静态测试数据分析')
    parser.add_argument('csv_file', help='T1 测试 CSV 文件路径')
    parser.add_argument('--plot', action='store_true', help='生成图表')
    parser.add_argument('--report', action='store_true', help='生成文本报告')
    parser.add_argument('--output-dir', help='输出目录')
    args = parser.parse_args()
    try:
        analyzer = T1Analyzer(args.csv_file)
        analyzer.analyze_t1_1_zero_offset()
        analyzer.analyze_t1_2_imu_stability()
        analyzer.analyze_t1_3_joint_velocity_noise()
        if args.plot:
            analyzer.plot_results(args.output_dir)
        if args.report:
            analyzer.generate_report()
        print("\n分析完成！")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
