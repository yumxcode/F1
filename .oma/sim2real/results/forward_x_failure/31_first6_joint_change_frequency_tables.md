# 31 First-6-Step Joint Change Frequency Tables

Source: 28 report canonical data scope, reusing the same first-6 touchdown events and `swing/touchdown` windows.

## Metric Notes

- `target_direction_change_rate_hz`: `pos_des_raw` first-difference sign reversal rate. It measures how often target direction changes.
- `joint_direction_change_rate_hz`: `joint_pos` first-difference sign reversal rate. It measures how often the actual joint reverses direction.
- `target_dominant_freq_hz` / `joint_dominant_freq_hz`: dominant frequency from a short-window DFT after mean removal. Because the windows are short, this column has low frequency resolution and often falls into the first DFT bin.
- `target_extrema_rate_hz` / `joint_extrema_rate_hz`: local extrema rate after a small diff epsilon. This is a more direct short-window turning-frequency metric.
- `target_path_rate_radps` / `joint_path_rate_radps`: cumulative absolute motion path per second. This measures movement intensity.
- `target_range_rad` / `joint_range_rad`: max-min amplitude inside the window.
- `tracking_err_rms_rad`: RMS of `pos_des_raw - joint_pos` without additional delay alignment in this table.
- `swing/event_leg`: the leg that will touchdown at the event; `swing/opposite_leg`: support-side opposite leg.
- `touchdown/landing_leg`: the leg that just touched down; `touchdown/stance_leg`: opposite support leg.

## Overview By Dataset / Window / Role / Joint

| dataset | window | role | joint | curves | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| real | swing | event_leg | ankle_pitch | 24 | 29.849 | 7.324 | 27.501 | 5.370 | 3.422 | 1.694 | 0.4068 | 0.3461 | 0.1749 |
| real | swing | event_leg | ankle_roll | 24 | 33.553 | 11.113 | 32.238 | 9.676 | 2.612 | 2.222 | 0.3735 | 0.2950 | 0.1693 |
| real | swing | event_leg | hip_pitch | 24 | 37.161 | 3.522 | 37.030 | 2.219 | 11.855 | 1.161 | 1.2698 | 0.2840 | 0.4073 |
| real | swing | event_leg | hip_roll | 24 | 32.887 | 6.783 | 28.962 | 3.139 | 8.263 | 0.311 | 1.0284 | 0.0755 | 0.3473 |
| real | swing | event_leg | knee_pitch | 24 | 28.791 | 4.063 | 28.527 | 3.529 | 5.825 | 3.782 | 0.9217 | 0.7671 | 0.4816 |
| real | swing | opposite_leg | ankle_pitch | 24 | 14.727 | 8.232 | 12.635 | 4.588 | 3.330 | 1.084 | 0.4491 | 0.2459 | 0.3328 |
| real | swing | opposite_leg | ankle_roll | 24 | 31.177 | 16.459 | 30.660 | 13.858 | 4.249 | 1.171 | 0.5878 | 0.2045 | 0.2560 |
| real | swing | opposite_leg | hip_pitch | 24 | 41.630 | 4.177 | 41.500 | 1.828 | 14.010 | 1.050 | 1.4748 | 0.2615 | 0.4516 |
| real | swing | opposite_leg | hip_roll | 24 | 30.452 | 9.148 | 27.329 | 4.820 | 12.089 | 0.482 | 1.4759 | 0.1070 | 0.6323 |
| real | swing | opposite_leg | knee_pitch | 24 | 32.329 | 4.039 | 32.064 | 2.357 | 5.005 | 1.710 | 0.7628 | 0.4422 | 0.2496 |
| real | touchdown | landing_leg | ankle_pitch | 24 | 14.743 | 6.772 | 13.592 | 5.284 | 2.941 | 2.005 | 0.2065 | 0.2638 | 0.3298 |
| real | touchdown | landing_leg | ankle_roll | 24 | 35.890 | 14.432 | 35.017 | 12.983 | 7.095 | 2.195 | 0.4457 | 0.2193 | 0.3113 |
| real | touchdown | landing_leg | hip_pitch | 24 | 47.620 | 2.106 | 47.342 | 1.213 | 16.609 | 1.409 | 0.8994 | 0.1931 | 0.4163 |
| real | touchdown | landing_leg | hip_roll | 24 | 33.373 | 10.536 | 29.223 | 5.219 | 19.167 | 0.560 | 1.2539 | 0.0681 | 0.8891 |
| real | touchdown | landing_leg | knee_pitch | 24 | 36.486 | 1.511 | 36.486 | 0.916 | 5.130 | 2.852 | 0.3203 | 0.4021 | 0.2559 |
| real | touchdown | stance_leg | ankle_pitch | 24 | 32.656 | 5.936 | 31.783 | 4.150 | 4.928 | 1.403 | 0.3185 | 0.1639 | 0.2257 |
| real | touchdown | stance_leg | ankle_roll | 24 | 37.375 | 8.555 | 36.185 | 8.258 | 3.457 | 2.002 | 0.2118 | 0.2225 | 0.1117 |
| real | touchdown | stance_leg | hip_pitch | 24 | 38.235 | 5.576 | 37.957 | 3.532 | 15.797 | 0.958 | 0.9600 | 0.1251 | 0.4072 |
| real | touchdown | stance_leg | hip_roll | 24 | 35.103 | 8.714 | 31.273 | 5.222 | 7.502 | 0.383 | 0.3924 | 0.0457 | 0.1481 |
| real | touchdown | stance_leg | knee_pitch | 24 | 28.585 | 3.830 | 28.287 | 2.361 | 8.594 | 2.860 | 0.7277 | 0.3785 | 0.4462 |
| sim | swing | event_leg | ankle_pitch | 24 | 17.587 | 8.716 | 15.889 | 7.548 | 2.464 | 1.209 | 0.3638 | 0.2241 | 0.1721 |
| sim | swing | event_leg | ankle_roll | 24 | 26.922 | 15.583 | 23.937 | 8.590 | 2.388 | 0.427 | 0.4397 | 0.0826 | 0.1595 |
| sim | swing | event_leg | hip_pitch | 24 | 22.469 | 4.808 | 22.070 | 2.333 | 5.055 | 0.797 | 0.6432 | 0.1922 | 0.1795 |
| sim | swing | event_leg | hip_roll | 24 | 26.877 | 8.989 | 23.636 | 5.602 | 9.220 | 0.466 | 1.5893 | 0.0859 | 0.5933 |
| sim | swing | event_leg | knee_pitch | 24 | 20.119 | 8.203 | 19.859 | 6.904 | 3.217 | 1.487 | 0.6846 | 0.4113 | 0.2713 |
| sim | swing | opposite_leg | ankle_pitch | 24 | 15.881 | 10.421 | 12.217 | 8.610 | 3.979 | 0.940 | 0.6952 | 0.1495 | 0.3556 |
| sim | swing | opposite_leg | ankle_roll | 24 | 22.359 | 12.372 | 20.161 | 8.085 | 1.753 | 0.704 | 0.3780 | 0.1401 | 0.1538 |
| sim | swing | opposite_leg | hip_pitch | 24 | 32.744 | 3.501 | 32.093 | 2.459 | 4.506 | 1.091 | 0.8230 | 0.2292 | 0.2729 |
| sim | swing | opposite_leg | hip_roll | 24 | 21.035 | 6.368 | 17.778 | 4.165 | 5.536 | 0.593 | 0.8988 | 0.1162 | 0.3842 |
| sim | swing | opposite_leg | knee_pitch | 24 | 14.559 | 3.249 | 14.046 | 0.391 | 4.550 | 1.447 | 1.0172 | 0.4324 | 0.2886 |
| sim | touchdown | landing_leg | ankle_pitch | 24 | 14.042 | 1.151 | 13.745 | 0.595 | 1.853 | 0.514 | 0.2089 | 0.0685 | 0.3131 |
| sim | touchdown | landing_leg | ankle_roll | 24 | 26.396 | 6.887 | 24.905 | 3.329 | 1.279 | 0.664 | 0.1268 | 0.0850 | 0.2573 |
| sim | touchdown | landing_leg | hip_pitch | 24 | 33.465 | 0.873 | 32.867 | 0.298 | 2.873 | 0.799 | 0.2348 | 0.1111 | 0.2103 |
| sim | touchdown | landing_leg | hip_roll | 24 | 33.596 | 0.595 | 33.276 | 0.595 | 4.326 | 0.668 | 0.3194 | 0.0925 | 0.6271 |
| sim | touchdown | landing_leg | knee_pitch | 24 | 22.306 | 4.094 | 21.390 | 0.618 | 1.113 | 0.403 | 0.1238 | 0.0503 | 0.1685 |
| sim | touchdown | stance_leg | ankle_pitch | 24 | 10.722 | 6.223 | 9.826 | 4.176 | 0.935 | 0.474 | 0.1179 | 0.0577 | 0.0359 |
| sim | touchdown | stance_leg | ankle_roll | 24 | 23.109 | 8.009 | 19.293 | 2.639 | 0.307 | 0.217 | 0.0295 | 0.0228 | 0.0102 |
| sim | touchdown | stance_leg | hip_pitch | 24 | 15.388 | 4.159 | 15.111 | 1.452 | 2.369 | 1.071 | 0.2633 | 0.1412 | 0.2143 |
| sim | touchdown | stance_leg | hip_roll | 24 | 21.195 | 2.685 | 20.021 | 0.873 | 1.869 | 0.437 | 0.1634 | 0.0595 | 0.1032 |
| sim | touchdown | stance_leg | knee_pitch | 24 | 2.004 | 6.844 | 2.004 | 4.712 | 3.642 | 1.153 | 0.4928 | 0.1339 | 0.1888 |
