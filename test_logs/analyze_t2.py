#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T2 动态性能对比测试数据分析脚本
用于分析 T2-2（步态周期）、T2-3（关节轨迹）、T2-4（机身姿态）、T2-5（网络输出）测试数据
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class T2Analyzer:
    def __init__(self, data_dir, timestamp=None):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"目录不存在: {data_dir}")
        if timestamp:
            self.gait_file = self.data_dir / f"t22_gait_{timestamp}.csv"
            self.joint_file = self.data_dir / f"t23_joint_{timestamp}.csv"
            self.pose_file = self.data_dir / f"t24_pose_{timestamp}.csv"
            self.action_file = self.data_dir / f"t25_action_{timestamp}.csv"
        else:
            gait_files = sorted(self.data_dir.glob("t22_gait_*.csv"))
            if not gait_files:
                raise FileNotFoundError("未找到 T2 测试数据文件")
            latest = gait_files[-1]
            timestamp = latest.stem.replace("t22_gait_", "")
            self.gait_file = latest
            self.joint_file = self.data_dir / f"t23_joint_{timestamp}.csv"
            self.pose_file = self.data_dir / f"t24_pose_{timestamp}.csv"
            self.action_file = self.data_dir / f"t25_action_{timestamp}.csv"

        print(f"正在读取 T2 测试数据 (timestamp: {timestamp})...")
        self.df_gait = pd.read_csv(self.gait_file)
        self.df_joint = pd.read_csv(self.joint_file)
        self.df_pose = pd.read_csv(self.pose_file)
        self.df_action = pd.read_csv(self.action_file)
        self.joint_names = [col.replace('pos_', '') for col in self.df_joint.columns if col.startswith('pos_')]
        print(f"数据行数: {len(self.df_gait)}, 关节数量: {len(self.joint_names)}")
        print(f"采样时长: {(self.df_gait['timestamp_ns'].iloc[-1] - self.df_gait['timestamp_ns'].iloc[0]) / 1e9:.2f} 秒")

    def analyze_t2_2_gait_cycle(self):
        """T2-2: 步态周期分析"""
        print("\n" + "="*60)
        print("T2-2: 步态周期分析")
        print("="*60)
        cycles = self.df_gait[self.df_gait['cycle_time_ms'] > 0]['cycle_time_ms']
        if len(cycles) == 0:
            print("警告: 未检测到有效的步态周期数据")
            return None
        print(f"步态周期统计:")
        print(f"  均值: {cycles.mean():.2f} ms, 标准差: {cycles.std():.2f} ms")
        print(f"  最小值: {cycles.min():.2f} ms, 最大值: {cycles.max():.2f} ms")
        print(f"  变异系数: {cycles.std()/cycles.mean()*100:.2f}%, 检测周期数: {len(cycles)}")
        status = "✓ 步态周期稳定性良好" if cycles.std() / cycles.mean() < 0.1 else "✗ 步态周期波动较大"
        print(f"  {status}")
        print(f"\n足端接触率: 左脚={self.df_gait['left_contact'].mean()*100:.1f}%, "
              f"右脚={self.df_gait['right_contact'].mean()*100:.1f}%")

    def analyze_t2_3_joint_tracking(self):
        """T2-3: 关节轨迹跟踪误差分析"""
        print("\n" + "="*60)
        print("T2-3: 关节轨迹跟踪误差分析")
        print("="*60)
        results = []
        for joint in self.joint_names:
            error = (self.df_joint[f'pos_{joint}'] - self.df_joint[f'target_{joint}']).abs()
            error_mean = error.mean()
            error_rms = np.sqrt((error**2).mean())
            results.append({'joint': joint, 'error_mean': error_mean, 'error_max': error.max(), 'error_rms': error_rms})
            threshold = 0.15 if 'knee' in joint else 0.12 if 'ankle' in joint else 0.10
            status = "✓ 通过" if error_mean < threshold else "✗ 超标"
            print(f"{joint:20s}: 均值={error_mean:.4f} rad, 最大={error.max():.4f} rad, RMS={error_rms:.4f} rad  {status}")
        return pd.DataFrame(results)

    def analyze_t2_4_body_pose(self):
        """T2-4: 机身姿态分析"""
        print("\n" + "="*60)
        print("T2-4: 机身姿态分析")
        print("="*60)
        print("\n欧拉角统计:")
        for col, name in zip(['euler_x', 'euler_y', 'euler_z'], ['Roll', 'Pitch', 'Yaw']):
            mean_val = self.df_pose[col].mean()
            std_val = self.df_pose[col].std()
            print(f"{name:6s}: 均值={mean_val:+.4f} rad ({mean_val*57.3:+.2f}°), 标准差={std_val:.4f} rad")
        print("\n角速度统计:")
        for col in ['ang_vel_x', 'ang_vel_y', 'ang_vel_z']:
            rms_val = np.sqrt((self.df_pose[col]**2).mean())
            print(f"{col:12s}: RMS={rms_val:.4f} rad/s, 最大={self.df_pose[col].abs().max():.4f} rad/s")

    def analyze_t2_5_action_output(self):
        """T2-5: 网络输出 Action 分析"""
        print("\n" + "="*60)
        print("T2-5: 网络输出 Action 分析")
        print("="*60)
        saturation_rate = (self.df_action['clip_count'] > 0).sum() / len(self.df_action)
        print(f"Action 饱和率: {saturation_rate*100:.2f}%, 平均 clip 关节数: {self.df_action['clip_count'].mean():.2f}")
        if saturation_rate < 0.05:
            print("  ✓ 饱和率良好 (< 5%)")
        elif saturation_rate < 0.15:
            print("  ⚠ 饱和率可接受 (< 15%)")
        else:
            print("  ✗ 饱和率过高 (≥ 15%)")

    def plot_results(self, output_dir=None):
        if output_dir is None:
            output_dir = self.data_dir
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        time_gait = (self.df_gait['timestamp_ns'] - self.df_gait['timestamp_ns'].iloc[0]) / 1e9
        time_joint = (self.df_joint['timestamp_ns'] - self.df_joint['timestamp_ns'].iloc[0]) / 1e9
        time_pose = (self.df_pose['timestamp_ns'] - self.df_pose['timestamp_ns'].iloc[0]) / 1e9

        # 图1: 步态周期
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        axes[0].plot(time_gait, self.df_gait['left_contact'], label='Left', linewidth=1)
        axes[0].plot(time_gait, self.df_gait['right_contact'], label='Right', linewidth=1)
        axes[0].set_title('Foot Contact State')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        valid = self.df_gait[self.df_gait['cycle_time_ms'] > 0]
        if len(valid) > 0:
            vt = (valid['timestamp_ns'] - self.df_gait['timestamp_ns'].iloc[0]) / 1e9
            axes[1].scatter(vt, valid['cycle_time_ms'], s=20)
            axes[1].axhline(y=valid['cycle_time_ms'].mean(), color='r', linestyle='--',
                           label=f'Mean: {valid["cycle_time_ms"].mean():.1f} ms')
            axes[1].set_title('Gait Cycle Time')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't2_2_gait_cycle.png', dpi=150)
        print(f"\n已保存图表: {output_dir / 't2_2_gait_cycle.png'}")
        plt.close()

        # 图2: 关节轨迹跟踪
        selected = [j for j in self.joint_names if 'knee' in j or 'hip_pitch' in j][:6]
        fig, axes = plt.subplots(3, 2, figsize=(14, 10))
        axes = axes.flatten()
        for idx, joint in enumerate(selected):
            axes[idx].plot(time_joint, self.df_joint[f'pos_{joint}'], label='Actual', linewidth=1)
            axes[idx].plot(time_joint, self.df_joint[f'target_{joint}'], label='Target', linestyle='--', linewidth=1)
            axes[idx].set_title(f'{joint}')
            axes[idx].legend()
            axes[idx].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't2_3_joint_tracking.png', dpi=150)
        print(f"已保存图表: {output_dir / 't2_3_joint_tracking.png'}")
        plt.close()

        # 图3: 机身姿态
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        for col, name in zip(['euler_x', 'euler_y', 'euler_z'], ['Roll', 'Pitch', 'Yaw']):
            axes[0].plot(time_pose, self.df_pose[col] * 57.3, label=name, linewidth=1)
        axes[0].set_title('Body Euler Angles')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        for col in ['ang_vel_x', 'ang_vel_y', 'ang_vel_z']:
            axes[1].plot(time_pose, self.df_pose[col], label=col, linewidth=1)
        axes[1].set_title('Body Angular Velocity')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / 't2_4_body_pose.png', dpi=150)
        print(f"已保存图表: {output_dir / 't2_4_body_pose.png'}")
        plt.close()


def main():
    parser = argparse.ArgumentParser(description='T2 动态性能测试数据分析')
    parser.add_argument('--data-dir', default='test_logs', help='数据目录路径')
    parser.add_argument('--timestamp', help='时间戳')
    parser.add_argument('--plot', action='store_true', help='生成图表')
    args = parser.parse_args()
    try:
        analyzer = T2Analyzer(args.data_dir, args.timestamp)
        analyzer.analyze_t2_2_gait_cycle()
        analyzer.analyze_t2_3_joint_tracking()
        analyzer.analyze_t2_4_body_pose()
        analyzer.analyze_t2_5_action_output()
        if args.plot:
            analyzer.plot_results()
        print("\n分析完成！")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
