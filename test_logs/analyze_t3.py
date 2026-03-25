#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T3 电机电流监测测试数据分析脚本
用于分析 T3-1（峰值电流）、T3-2（平均功耗）、T3-3（电流波形）测试数据
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class T3Analyzer:
    def __init__(self, csv_file):
        self.csv_file = Path(csv_file)
        if not self.csv_file.exists():
            raise FileNotFoundError(f"文件不存在: {csv_file}")
        print(f"正在读取文件: {self.csv_file}")
        self.df = pd.read_csv(csv_file)
        self.joint_names = [col.replace('current_', '') for col in self.df.columns if col.startswith('current_')]
        self.motor_config = self._default_motor_config()
        print(f"数据行数: {len(self.df)}, 关节数量: {len(self.joint_names)}")
        print(f"采样时长: {(self.df['timestamp_ns'].iloc[-1] - self.df['timestamp_ns'].iloc[0]) / 1e9:.2f} 秒")

    def _default_motor_config(self):
        """默认电机配置（额定电流和峰值限制）"""
        config = {}
        for joint in self.joint_names:
            if 'hip_yaw' in joint or 'hip_roll' in joint:
                config[joint] = {'rated_current': 8.0, 'peak_limit': 12.0}
            elif 'hip_pitch' in joint or 'knee' in joint:
                config[joint] = {'rated_current': 12.0, 'peak_limit': 18.0}
            elif 'ankle' in joint:
                config[joint] = {'rated_current': 6.0, 'peak_limit': 10.0}
            else:
                config[joint] = {'rated_current': 10.0, 'peak_limit': 15.0}
        return config

    def analyze_t3_1_peak_current(self):
        """T3-1: 峰值电流分析"""
        print("\n" + "="*60)
        print("T3-1: 峰值电流分析")
        print("="*60)
        results = []
        for joint in self.joint_names:
            col = f'current_{joint}'
            peak = self.df[col].abs().max()
            mean_abs = self.df[col].abs().mean()
            rated = self.motor_config[joint]['rated_current']
            peak_limit = self.motor_config[joint]['peak_limit']
            margin = (peak_limit - peak) / peak_limit * 100
            results.append({
                'joint': joint, 'peak_current': peak, 'mean_abs_current': mean_abs,
                'rated_current': rated, 'peak_limit': peak_limit, 'margin_pct': margin
            })
            if peak > peak_limit:
                status = "✗ 超过峰值限制"
            elif peak > rated:
                status = "⚠ 超过额定值"
            else:
                status = "✓ 正常"
            print(f"{joint:20s}: 峰值={peak:.3f}A, 均值={mean_abs:.3f}A, "
                  f"额定={rated:.1f}A, 峰值限={peak_limit:.1f}A, 裕度={margin:.1f}%  {status}")
        return pd.DataFrame(results)

    def analyze_t3_2_average_power(self):
        """T3-2: 平均功耗分析"""
        print("\n" + "="*60)
        print("T3-2: 平均功耗估算")
        print("="*60)
        bus_voltage = 48.0  # 总线电压，需根据实际调整
        total_power = 0.0
        for joint in self.joint_names:
            col = f'current_{joint}'
            rms_current = np.sqrt((self.df[col]**2).mean())
            power = rms_current * bus_voltage  # 简化估算
            total_power += power
            print(f"{joint:20s}: RMS电流={rms_current:.3f}A, 估算功率={power:.1f}W")
        print(f"\n总估算功率: {total_power:.1f} W")
        return total_power

    def analyze_t3_3_waveform(self):
        """T3-3: 电流波形统计分析"""
        print("\n" + "="*60)
        print("T3-3: 电流波形统计")
        print("="*60)
        results = []
        for joint in self.joint_names:
            col = f'current_{joint}'
            data = self.df[col]
            stats = {
                'joint': joint,
                'mean': data.mean(), 'std': data.std(),
                'rms': np.sqrt((data**2).mean()),
                'peak_pos': data.max(), 'peak_neg': data.min(),
                'crest_factor': data.abs().max() / np.sqrt((data**2).mean()) if np.sqrt((data**2).mean()) > 0 else 0,
            }
            results.append(stats)
            print(f"{joint:20s}: 均值={stats['mean']:+.3f}A, 标准差={stats['std']:.3f}A, "
                  f"RMS={stats['rms']:.3f}A, 峰值因子={stats['crest_factor']:.2f}")

        # 电流尖峰检测
        print("\n电流尖峰检测:")
        for joint in self.joint_names:
            col = f'current_{joint}'
            data = self.df[col]
            threshold = data.abs().mean() + 3 * data.abs().std()
            spikes = (data.abs() > threshold).sum()
            spike_pct = spikes / len(data) * 100
            status = "✓ 正常" if spike_pct < 5 else "⚠ 尖峰较多"
            print(f"{joint:20s}: 尖峰阈值={threshold:.3f}A, 尖峰数={spikes}, 占比={spike_pct:.2f}%  {status}")

        return pd.DataFrame(results)

    def plot_results(self, output_dir=None):
        if output_dir is None:
            output_dir = self.csv_file.parent
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        time_s = (self.df['timestamp_ns'] - self.df['timestamp_ns'].iloc[0]) / 1e9

        # 图1: 电流时间序列
        n_joints = min(len(self.joint_names), 12)
        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        axes = axes.flatten()
        for idx in range(n_joints):
            joint = self.joint_names[idx]
            col = f'current_{joint}'
            axes[idx].plot(time_s, self.df[col], linewidth=0.5)
            axes[idx].axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
            rated = self.motor_config[joint]['rated_current']
            axes[idx].axhline(y=rated, color='orange', linestyle='--', linewidth=1, label=f'Rated {rated}A')
            axes[idx].axhline(y=-rated, color='orange', linestyle='--', linewidth=1)
            axes[idx].set_title(f'{joint}')
            axes[idx].set_xlabel('Time (s)')
            axes[idx].set_ylabel('Current (A)')
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't3_current_timeseries.png', dpi=150)
        print(f"\n已保存图表: {output_dir / 't3_current_timeseries.png'}")
        plt.close()

        # 图2: 电流分布直方图
        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        axes = axes.flatten()
        for idx in range(n_joints):
            joint = self.joint_names[idx]
            col = f'current_{joint}'
            axes[idx].hist(self.df[col], bins=50, alpha=0.7, density=True)
            axes[idx].set_title(f'{joint}')
            axes[idx].set_xlabel('Current (A)')
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't3_current_distribution.png', dpi=150)
        print(f"已保存图表: {output_dir / 't3_current_distribution.png'}")
        plt.close()

        # 图3: 电流 vs 速度散点图
        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        axes = axes.flatten()
        for idx in range(n_joints):
            joint = self.joint_names[idx]
            cur_col = f'current_{joint}'
            vel_col = f'vel_{joint}'
            if vel_col in self.df.columns:
                axes[idx].scatter(self.df[vel_col], self.df[cur_col], s=1, alpha=0.3)
                axes[idx].set_title(f'{joint}')
                axes[idx].set_xlabel('Velocity (rad/s)')
                axes[idx].set_ylabel('Current (A)')
                axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't3_current_vs_velocity.png', dpi=150)
        print(f"已保存图表: {output_dir / 't3_current_vs_velocity.png'}")
        plt.close()

        # 图4: 峰值电流对比条形图
        peaks = [self.df[f'current_{j}'].abs().max() for j in self.joint_names]
        rated = [self.motor_config[j]['rated_current'] for j in self.joint_names]
        x = np.arange(len(self.joint_names))
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.bar(x - 0.2, peaks, 0.4, label='Peak Current', color='steelblue')
        ax.bar(x + 0.2, rated, 0.4, label='Rated Current', color='orange', alpha=0.7)
        ax.set_xlabel('Joint')
        ax.set_ylabel('Current (A)')
        ax.set_title('Peak Current vs Rated Current')
        ax.set_xticks(x)
        ax.set_xticklabels(self.joint_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        fig.savefig(output_dir / 't3_peak_current_comparison.png', dpi=150)
        print(f"已保存图表: {output_dir / 't3_peak_current_comparison.png'}")
        plt.close()

    def generate_report(self, output_file=None):
        if output_file is None:
            output_file = self.csv_file.parent / f"{self.csv_file.stem}_report.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\nT3 电机电流测试分析报告\n" + "="*60 + "\n")
            f.write(f"数据文件: {self.csv_file}\n")
            f.write(f"数据行数: {len(self.df)}\n")
            f.write(f"采样时长: {(self.df['timestamp_ns'].iloc[-1] - self.df['timestamp_ns'].iloc[0]) / 1e9:.2f} 秒\n\n")
            df_peak = self.analyze_t3_1_peak_current()
            f.write(df_peak.to_string(index=False) + "\n\n")
            total_power = self.analyze_t3_2_average_power()
            f.write(f"总估算功率: {total_power:.1f} W\n\n")
            df_wave = self.analyze_t3_3_waveform()
            f.write(df_wave.to_string(index=False) + "\n")
        print(f"\n已保存报告: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='T3 电机电流测试数据分析')
    parser.add_argument('csv_file', nargs='?', help='T3 测试 CSV 文件路径')
    parser.add_argument('--data-dir', default='test_logs', help='数据目录路径')
    parser.add_argument('--plot', action='store_true', help='生成图表')
    parser.add_argument('--report', action='store_true', help='生成文本报告')
    args = parser.parse_args()
    try:
        if args.csv_file:
            csv_file = args.csv_file
        else:
            data_dir = Path(args.data_dir)
            files = sorted(data_dir.glob("t3_current_*.csv"))
            if not files:
                print("错误: 未找到 T3 测试数据文件")
                sys.exit(1)
            csv_file = files[-1]
            print(f"自动选择最新文件: {csv_file}")
        analyzer = T3Analyzer(csv_file)
        analyzer.analyze_t3_1_peak_current()
        analyzer.analyze_t3_2_average_power()
        analyzer.analyze_t3_3_waveform()
        if args.plot:
            analyzer.plot_results()
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
