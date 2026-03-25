#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试数据分析脚本
一键分析 T1/T2/T3 所有测试数据并生成完整报告
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime


def find_latest_files(data_dir):
    """查找最新的测试数据文件"""
    data_dir = Path(data_dir)
    files = {}

    # T1
    t1_files = sorted(data_dir.glob("t1_static_*.csv"))
    if t1_files:
        files['t1'] = t1_files[-1]

    # T2
    t22_files = sorted(data_dir.glob("t22_gait_*.csv"))
    if t22_files:
        ts = t22_files[-1].stem.replace("t22_gait_", "")
        files['t2_timestamp'] = ts
        files['t2_gait'] = t22_files[-1]

    # T3
    t3_files = sorted(data_dir.glob("t3_current_*.csv"))
    if t3_files:
        files['t3'] = t3_files[-1]

    # T1-4
    t14_files = sorted(data_dir.glob("t14_delay_*.csv"))
    if t14_files:
        files['t14'] = t14_files[-1]

    return files


def list_available_data(data_dir):
    """列出所有可用的测试数据"""
    data_dir = Path(data_dir)
    print("="*60)
    print("可用测试数据")
    print("="*60)

    for pattern, name in [
        ("t1_static_*.csv", "T1 静态测试"),
        ("t14_delay_*.csv", "T1-4 延迟测试"),
        ("t22_gait_*.csv", "T2-2 步态周期"),
        ("t23_joint_*.csv", "T2-3 关节轨迹"),
        ("t24_pose_*.csv", "T2-4 机身姿态"),
        ("t25_action_*.csv", "T2-5 网络输出"),
        ("t3_current_*.csv", "T3 电机电流"),
    ]:
        files = sorted(data_dir.glob(pattern))
        if files:
            print(f"\n{name} ({len(files)} 个文件):")
            for f in files[-3:]:
                size_kb = f.stat().st_size / 1024
                print(f"  {f.name}  ({size_kb:.1f} KB)")
        else:
            print(f"\n{name}: 无数据")


def analyze_latest(data_dir, plot=False, report=False):
    """分析最新的测试数据"""
    files = find_latest_files(data_dir)
    if not files:
        print("错误: 未找到任何测试数据")
        return

    output_dir = Path(data_dir) / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(exist_ok=True)
    print(f"\n分析输出目录: {output_dir}")

    summary_lines = []
    summary_lines.append("="*60)
    summary_lines.append("Sim-to-Real 综合测试分析报告")
    summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("="*60)

    # T1 分析
    if 't1' in files:
        print("\n" + "="*60)
        print(">>> T1 静态测试分析")
        print("="*60)
        try:
            from analyze_t1 import T1Analyzer
            analyzer = T1Analyzer(files['t1'])
            analyzer.analyze_t1_1_zero_offset()
            analyzer.analyze_t1_2_imu_stability()
            analyzer.analyze_t1_3_joint_velocity_noise()
            if plot:
                analyzer.plot_results(output_dir)
            if report:
                analyzer.generate_report(output_dir / 't1_report.txt')
            summary_lines.append("\n[T1] 静态测试: ✓ 分析完成")
        except Exception as e:
            print(f"T1 分析失败: {e}")
            summary_lines.append(f"\n[T1] 静态测试: ✗ 分析失败 ({e})")
    else:
        summary_lines.append("\n[T1] 静态测试: - 无数据")

    # T2 分析
    if 't2_timestamp' in files:
        print("\n" + "="*60)
        print(">>> T2 动态性能测试分析")
        print("="*60)
        try:
            from analyze_t2 import T2Analyzer
            analyzer = T2Analyzer(data_dir, files['t2_timestamp'])
            analyzer.analyze_t2_2_gait_cycle()
            analyzer.analyze_t2_3_joint_tracking()
            analyzer.analyze_t2_4_body_pose()
            analyzer.analyze_t2_5_action_output()
            if plot:
                analyzer.plot_results(output_dir)
            summary_lines.append("[T2] 动态测试: ✓ 分析完成")
        except Exception as e:
            print(f"T2 分析失败: {e}")
            summary_lines.append(f"[T2] 动态测试: ✗ 分析失败 ({e})")
    else:
        summary_lines.append("[T2] 动态测试: - 无数据")

    # T3 分析
    if 't3' in files:
        print("\n" + "="*60)
        print(">>> T3 电机电流测试分析")
        print("="*60)
        try:
            from analyze_t3 import T3Analyzer
            analyzer = T3Analyzer(files['t3'])
            analyzer.analyze_t3_1_peak_current()
            analyzer.analyze_t3_2_average_power()
            analyzer.analyze_t3_3_waveform()
            if plot:
                analyzer.plot_results(output_dir)
            if report:
                analyzer.generate_report(output_dir / 't3_report.txt')
            summary_lines.append("[T3] 电流测试: ✓ 分析完成")
        except Exception as e:
            print(f"T3 分析失败: {e}")
            summary_lines.append(f"[T3] 电流测试: ✗ 分析失败 ({e})")
    else:
        summary_lines.append("[T3] 电流测试: - 无数据")

    # 保存综合报告
    if report:
        summary_file = output_dir / 'summary_report.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_lines) + '\n')
        print(f"\n综合报告已保存: {summary_file}")

    print("\n" + "="*60)
    print("综合分析完成！")
    print("="*60)
    for line in summary_lines:
        if line.startswith('['):
            print(f"  {line}")


def main():
    parser = argparse.ArgumentParser(description='综合测试数据分析工具')
    parser.add_argument('--data-dir', default='test_logs', help='数据目录路径')
    parser.add_argument('--list', action='store_true', help='列出所有可用的测试数据')
    parser.add_argument('--analyze-latest', action='store_true', help='分析最新测试数据')
    parser.add_argument('--plot', action='store_true', help='生成图表')
    parser.add_argument('--report', action='store_true', help='生成文本报告')
    args = parser.parse_args()

    if args.list:
        list_available_data(args.data_dir)
    elif args.analyze_latest:
        analyze_latest(args.data_dir, args.plot, args.report)
    else:
        parser.print_help()
        print("\n示例:")
        print("  python analyze_all.py --list")
        print("  python analyze_all.py --analyze-latest --plot --report")


if __name__ == '__main__':
    main()
