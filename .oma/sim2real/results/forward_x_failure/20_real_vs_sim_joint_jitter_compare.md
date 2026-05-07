# 20 Real vs Sim Swing/Touchdown Joint Adjustment/Jitter Compare

- Scope: real `t27` all-ankle 4 cases vs sim `t27` 4 cases.
- Windows: `swing = touchdown-350ms .. touchdown-20ms`, `touchdown = touchdown-50ms .. touchdown+100ms`.
- Signal pair: `pos_des_raw_<side>_ankle_<axis>_joint` as joint output proxy, `pos_<side>_ankle_<axis>_joint` as realized joint.
- Axes: ankle `roll` and `pitch`; sides: left and right.
- High-frequency metric: `hp_rms = signal - 5-sample moving average` RMS, emphasizing local shake.
- Adjustment-size metrics: `range`, `path_length`, `net_delta_abs`; these capture large corrections even when not high-frequency.
- Adjustment-frequency metrics: `direction_change_rate_hz`, `dominant_freq_hz`, `flip_rate`; these capture how often the correction direction changes.

## Metric Dictionary

| column | meaning | unit / reading |
|---|---|---|
| `stage` | Data source group. `real` is hardware log, `sim` is simulation log. | category |
| `window` | Touchdown-relative phase window. `swing` is `touchdown-350ms .. touchdown-20ms`; `touchdown` is `touchdown-50ms .. touchdown+100ms`. | category |
| `axis` | Ankle axis being evaluated. | `roll` or `pitch` |
| `events` | Number of touchdown-window samples after aggregation. Stage summary aggregates 4 cases x 4 early touchdowns x 2 sides = 32 events per stage/window/axis. | count |
| `out hp` | High-pass RMS of policy/raw joint output proxy `pos_des_raw`. Computed as RMS of `signal - 5-sample moving_average(signal)`. | rad; larger means output has stronger local high-frequency shake |
| `joint hp` | High-pass RMS of realized joint position `pos`. Same computation as `out hp`. | rad; larger means actual joint has stronger local high-frequency shake |
| `hp ratio` | `joint hp / out hp`. | dimensionless; larger than 1 means realized joint high-frequency residual exceeds output residual |
| `out range` | `max(output) - min(output)` inside the window. | rad; output adjustment amplitude |
| `joint range` | `max(joint) - min(joint)` inside the window. | rad; realized joint adjustment amplitude |
| `out path` | Sum of absolute frame-to-frame output changes: `sum(abs(diff(output)))`. | rad; cumulative output adjustment distance |
| `joint path` | Sum of absolute frame-to-frame realized joint changes: `sum(abs(diff(joint)))`. | rad; cumulative realized joint adjustment distance |
| `out dir hz` | Direction-change rate of output, based on sign flips of first differences after a small epsilon filter. | Hz; larger means output reverses correction direction more often |
| `joint dir hz` | Direction-change rate of realized joint, same method as `out dir hz`. | Hz; larger means actual joint reverses correction direction more often |
| `out dom hz` | Dominant frequency of the output signal in the local window, estimated by direct DFT after mean removal. | Hz; main low/window-scale oscillation component, not alone a jitter verdict |
| `joint dom hz` | Dominant frequency of the realized joint signal in the local window, same method as `out dom hz`. | Hz; main realized-joint oscillation component |
| `track err` | RMS tracking error between output and realized joint: `rms(output - joint)`. | rad; larger means output-to-joint realization gap is larger |

## Stage Summary

| stage | window | axis | events | out hp | joint hp | hp ratio | out range | joint range | out path | joint path | out dir hz | joint dir hz | out dom hz | joint dom hz | track err |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| real | swing | pitch | 32 | 0.0456 | 0.0095 | 0.2942 | 0.4504 | 0.2397 | 1.0767 | 0.3956 | 22.2275 | 8.3473 | 8.2465 | 3.3302 | 0.2321 |
| real | swing | roll | 32 | 0.0349 | 0.0105 | 0.4252 | 0.4307 | 0.2364 | 1.0687 | 0.4924 | 31.9984 | 14.1360 | 3.8125 | 3.8125 | 0.1986 |
| real | touchdown | pitch | 32 | 0.0611 | 0.0106 | 0.2057 | 0.3310 | 0.2267 | 0.8033 | 0.2587 | 31.0239 | 8.5605 | 12.5918 | 6.7362 | 0.2630 |
| real | touchdown | roll | 32 | 0.0565 | 0.0135 | 0.3402 | 0.3645 | 0.2115 | 0.8517 | 0.2966 | 40.5665 | 15.2104 | 10.1735 | 7.1663 | 0.2136 |
| sim | swing | pitch | 32 | 0.0315 | 0.0074 | 0.4640 | 0.4878 | 0.1676 | 0.7914 | 0.2638 | 12.0581 | 7.7281 | 3.5116 | 3.0435 | 0.2024 |
| sim | swing | roll | 32 | 0.0204 | 0.0033 | 0.1834 | 0.3101 | 0.0804 | 0.5456 | 0.1263 | 22.9628 | 12.0039 | 5.3345 | 3.5230 | 0.1252 |
| sim | touchdown | pitch | 32 | 0.0424 | 0.0144 | 0.3497 | 0.3641 | 0.1344 | 0.5240 | 0.2105 | 20.8196 | 15.0551 | 12.0434 | 7.6171 | 0.2262 |
| sim | touchdown | roll | 32 | 0.0294 | 0.0076 | 0.4412 | 0.2608 | 0.1016 | 0.3965 | 0.1315 | 28.9982 | 19.0338 | 9.0497 | 7.6320 | 0.1463 |

### Stage Summary Analysis

- `real` 的问题不是单一高频抖动。新 kinematic touchdown 窗口下，real 的 `joint range/joint path/track err` 仍整体高于 sim，说明主要差异仍是更大的真实关节调整负担和更差的 output-to-joint 兑现。
- `swing` 阶段主要表现为“调整更大”，不是“所有高频都更大”。例如 `pitch swing` 的 `joint hp` real/sim 为 `1.2837`x，但 `joint range` 和 `joint path` 仍分别为 `1.4304`x / `1.4996`x，说明 swing 更像过量姿态修正。
- `touchdown` 才是差异最集中的窗口。`roll touchdown` 的 `joint hp/range/path/dir-rate` real 相对 sim 分别为 `1.7630`x / `2.0818`x / `2.2553`x / `0.7991`x，这是当前最重的异常点。
- `pitch touchdown` 的读法需要降级：real 的 `joint hp` 不高于 sim，但 `joint range/path/track err` 仍高于 sim，因此它更像接触窗口内的大幅姿态兑现问题，而不是 pitch 高频抖动问题。
- `hp ratio` 在 real 全部小于 `1`，说明真实 joint 没有把输出高频进一步放大成更大的高频噪声，反而滤掉了一部分高频；但 real 的 `joint range/joint path/track err` 仍明显更大，说明问题更像“大幅度、长路径的纠偏 + 更差的输出兑现”，而不是纯高频抖振。

## Stage-Side Summary

| stage | window | side | axis | events | joint hp | joint range | joint path | joint dir hz | joint dom hz | track err |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| real | swing | left | pitch | 16 | 0.0095 | 0.2550 | 0.4433 | 6.4606 | 3.2327 | 0.2354 |
| real | swing | left | roll | 16 | 0.0105 | 0.2984 | 0.6036 | 12.1568 | 3.6171 | 0.2353 |
| real | swing | right | pitch | 16 | 0.0094 | 0.2245 | 0.3479 | 10.2340 | 3.4277 | 0.2288 |
| real | swing | right | roll | 16 | 0.0105 | 0.1744 | 0.3813 | 16.1153 | 4.0078 | 0.1619 |
| real | touchdown | left | pitch | 16 | 0.0121 | 0.2307 | 0.2748 | 8.9772 | 6.7340 | 0.2646 |
| real | touchdown | left | roll | 16 | 0.0159 | 0.2792 | 0.3684 | 11.3422 | 6.7340 | 0.2578 |
| real | touchdown | right | pitch | 16 | 0.0092 | 0.2228 | 0.2426 | 8.1438 | 6.7385 | 0.2614 |
| real | touchdown | right | roll | 16 | 0.0110 | 0.1438 | 0.2247 | 19.0785 | 7.6274 | 0.1694 |
| sim | swing | left | pitch | 16 | 0.0099 | 0.1814 | 0.3060 | 9.7638 | 3.0435 | 0.1831 |
| sim | swing | left | roll | 16 | 0.0043 | 0.1177 | 0.1804 | 14.1630 | 3.0435 | 0.1570 |
| sim | swing | right | pitch | 16 | 0.0048 | 0.1538 | 0.2216 | 5.6924 | 3.0435 | 0.2217 |
| sim | swing | right | roll | 16 | 0.0022 | 0.0430 | 0.0722 | 9.8448 | 4.0025 | 0.0934 |
| sim | touchdown | left | pitch | 16 | 0.0160 | 0.1504 | 0.2316 | 15.5875 | 7.6320 | 0.2533 |
| sim | touchdown | left | roll | 16 | 0.0101 | 0.1505 | 0.1875 | 19.9291 | 8.0785 | 0.2309 |
| sim | touchdown | right | pitch | 16 | 0.0128 | 0.1185 | 0.1894 | 14.5227 | 7.6023 | 0.1991 |
| sim | touchdown | right | roll | 16 | 0.0052 | 0.0526 | 0.0755 | 18.1384 | 7.1855 | 0.0616 |

### Stage-Side Summary Analysis

- real swing roll: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `right`，`track err` 更大的是 `left`。 左右数值分别为 range `0.2984` / `0.1744`，path `0.6036` / `0.3813`，dir-rate `12.1568` / `16.1153`。
- real swing pitch: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `right`，`track err` 更大的是 `left`。 左右数值分别为 range `0.2550` / `0.2245`，path `0.4433` / `0.3479`，dir-rate `6.4606` / `10.2340`。
- real touchdown roll: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `right`，`track err` 更大的是 `left`。 左右数值分别为 range `0.2792` / `0.1438`，path `0.3684` / `0.2247`，dir-rate `11.3422` / `19.0785`。
- real touchdown pitch: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `left`，`track err` 更大的是 `left`。 左右数值分别为 range `0.2307` / `0.2228`，path `0.2748` / `0.2426`，dir-rate `8.9772` / `8.1438`。
- sim swing roll: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `left`，`track err` 更大的是 `left`。 左右数值分别为 range `0.1177` / `0.0430`，path `0.1804` / `0.0722`，dir-rate `14.1630` / `9.8448`。
- sim swing pitch: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `left`，`track err` 更大的是 `right`。 左右数值分别为 range `0.1814` / `0.1538`，path `0.3060` / `0.2216`，dir-rate `9.7638` / `5.6924`。
- sim touchdown roll: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `left`，`track err` 更大的是 `left`。 左右数值分别为 range `0.1505` / `0.0526`，path `0.1875` / `0.0755`，dir-rate `19.9291` / `18.1384`。
- sim touchdown pitch: `range/path` 更重的是 `left` / `left`，`dir-rate` 更高的是 `left`，`track err` 更大的是 `left`。 左右数值分别为 range `0.1504` / `0.1185`，path `0.2316` / `0.1894`，dir-rate `15.5875` / `14.5227`。
- 从 `real` 侧读法看，`swing roll` 和 `touchdown roll` 都不是完全对称问题：左侧更偏“大幅修正”，右侧更偏“频繁反向修正”。这更像左右脚在不同子阶段承担了不同的补偿方式，而不是单脚统一高频炸掉。
- `real touchdown pitch` 在新窗口下左侧 `range/path/dir-rate/track err` 均略高，说明 pitch 接触窗更偏左侧兑现负担，而不是左右脚完全对称。
- `sim` 侧虽然也有左右差异，但 real 的 roll `joint range/path/track err` 仍明显更高，说明 real 仍存在更重的 touchdown 调整负担。

## Per-case Side Summary

| stage | case | side | axis | window | events | joint hp | joint range | joint path | joint dir hz | track err |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| real | 25/0.4 all_ankles | left | pitch | swing | 4 | 0.0107 | 0.2727 | 0.4514 | 4.7382 | 0.2351 |
| real | 25/0.4 all_ankles | left | pitch | touchdown | 4 | 0.0111 | 0.2210 | 0.2576 | 7.4180 | 0.2559 |
| real | 25/0.4 all_ankles | left | roll | swing | 4 | 0.0071 | 0.2360 | 0.4115 | 12.5512 | 0.2802 |
| real | 25/0.4 all_ankles | left | roll | touchdown | 4 | 0.0126 | 0.2308 | 0.2926 | 7.5554 | 0.3132 |
| real | 25/0.4 all_ankles | right | pitch | swing | 4 | 0.0074 | 0.1688 | 0.2450 | 13.3577 | 0.1977 |
| real | 25/0.4 all_ankles | right | pitch | touchdown | 4 | 0.0117 | 0.2019 | 0.2197 | 12.9129 | 0.2477 |
| real | 25/0.4 all_ankles | right | roll | swing | 4 | 0.0089 | 0.1153 | 0.2659 | 16.5837 | 0.1637 |
| real | 25/0.4 all_ankles | right | roll | touchdown | 4 | 0.0097 | 0.1063 | 0.1498 | 27.7490 | 0.1564 |
| real | 30/0.4 all_ankles | left | pitch | swing | 4 | 0.0113 | 0.2319 | 0.4508 | 5.4972 | 0.2184 |
| real | 30/0.4 all_ankles | left | pitch | touchdown | 4 | 0.0139 | 0.2344 | 0.2624 | 5.4947 | 0.2621 |
| real | 30/0.4 all_ankles | left | roll | swing | 4 | 0.0113 | 0.3047 | 0.5922 | 11.8482 | 0.2712 |
| real | 30/0.4 all_ankles | left | roll | touchdown | 4 | 0.0177 | 0.2518 | 0.3729 | 12.6378 | 0.3287 |
| real | 30/0.4 all_ankles | right | pitch | swing | 4 | 0.0050 | 0.1729 | 0.2858 | 7.8677 | 0.2301 |
| real | 30/0.4 all_ankles | right | pitch | touchdown | 4 | 0.0081 | 0.1829 | 0.2120 | 7.1431 | 0.2315 |
| real | 30/0.4 all_ankles | right | roll | swing | 4 | 0.0044 | 0.1215 | 0.2528 | 18.7911 | 0.1603 |
| real | 30/0.4 all_ankles | right | roll | touchdown | 4 | 0.0078 | 0.1233 | 0.1580 | 16.6214 | 0.1960 |
| real | 35/0.5 all_ankles | left | pitch | swing | 4 | 0.0086 | 0.3123 | 0.4986 | 6.9872 | 0.2334 |
| real | 35/0.5 all_ankles | left | pitch | touchdown | 4 | 0.0126 | 0.2294 | 0.3000 | 8.9472 | 0.2682 |
| real | 35/0.5 all_ankles | left | roll | swing | 4 | 0.0139 | 0.4024 | 0.8582 | 11.6512 | 0.2065 |
| real | 35/0.5 all_ankles | left | roll | touchdown | 4 | 0.0180 | 0.3298 | 0.4016 | 12.7935 | 0.2084 |
| real | 35/0.5 all_ankles | right | pitch | swing | 4 | 0.0208 | 0.3957 | 0.5900 | 6.2517 | 0.3072 |
| real | 35/0.5 all_ankles | right | pitch | touchdown | 4 | 0.0100 | 0.3010 | 0.3119 | 1.9231 | 0.3216 |
| real | 35/0.5 all_ankles | right | roll | swing | 4 | 0.0209 | 0.2876 | 0.5861 | 9.4777 | 0.1707 |
| real | 35/0.5 all_ankles | right | roll | touchdown | 4 | 0.0106 | 0.1556 | 0.2370 | 7.1797 | 0.1551 |
| real | 40/0.8 all_ankles | left | pitch | swing | 4 | 0.0076 | 0.2030 | 0.3724 | 8.6197 | 0.2545 |
| real | 40/0.8 all_ankles | left | pitch | touchdown | 4 | 0.0107 | 0.2379 | 0.2791 | 14.0488 | 0.2722 |
| real | 40/0.8 all_ankles | left | roll | swing | 4 | 0.0098 | 0.2504 | 0.5524 | 12.5767 | 0.1835 |
| real | 40/0.8 all_ankles | left | roll | touchdown | 4 | 0.0154 | 0.3044 | 0.4066 | 12.3820 | 0.1808 |
| real | 40/0.8 all_ankles | right | pitch | swing | 4 | 0.0043 | 0.1605 | 0.2708 | 13.4588 | 0.1803 |
| real | 40/0.8 all_ankles | right | pitch | touchdown | 4 | 0.0069 | 0.2054 | 0.2269 | 10.5962 | 0.2448 |
| real | 40/0.8 all_ankles | right | roll | swing | 4 | 0.0078 | 0.1732 | 0.4202 | 19.6085 | 0.1530 |
| real | 40/0.8 all_ankles | right | roll | touchdown | 4 | 0.0161 | 0.1899 | 0.3542 | 24.7640 | 0.1702 |
| sim | 2504 | left | pitch | swing | 4 | 0.0107 | 0.1532 | 0.2770 | 9.3321 | 0.1217 |
| sim | 2504 | left | pitch | touchdown | 4 | 0.0173 | 0.1533 | 0.2160 | 18.8247 | 0.2332 |
| sim | 2504 | left | roll | swing | 4 | 0.0023 | 0.0546 | 0.0741 | 11.0922 | 0.1534 |
| sim | 2504 | left | roll | touchdown | 4 | 0.0054 | 0.0477 | 0.0804 | 22.3972 | 0.3262 |
| sim | 2504 | right | pitch | swing | 4 | 0.0021 | 0.0880 | 0.1242 | 3.9105 | 0.2024 |
| sim | 2504 | right | pitch | touchdown | 4 | 0.0075 | 0.0936 | 0.1309 | 12.9162 | 0.1169 |
| sim | 2504 | right | roll | swing | 4 | 0.0008 | 0.0346 | 0.0439 | 4.7173 | 0.1159 |
| sim | 2504 | right | roll | touchdown | 4 | 0.0041 | 0.0424 | 0.0576 | 18.5498 | 0.0479 |
| sim | 3505 | left | pitch | swing | 4 | 0.0109 | 0.1646 | 0.3040 | 8.6717 | 0.1882 |
| sim | 3505 | left | pitch | touchdown | 4 | 0.0143 | 0.1498 | 0.2202 | 14.4636 | 0.2492 |
| sim | 3505 | left | roll | swing | 4 | 0.0035 | 0.1213 | 0.1775 | 15.8813 | 0.1797 |
| sim | 3505 | left | roll | touchdown | 4 | 0.0096 | 0.1426 | 0.1789 | 21.3519 | 0.2170 |
| sim | 3505 | right | pitch | swing | 4 | 0.0047 | 0.1444 | 0.2157 | 4.8148 | 0.2017 |
| sim | 3505 | right | pitch | touchdown | 4 | 0.0134 | 0.1189 | 0.1949 | 16.2498 | 0.2481 |
| sim | 3505 | right | roll | swing | 4 | 0.0021 | 0.0494 | 0.0684 | 8.8230 | 0.0736 |
| sim | 3505 | right | roll | touchdown | 4 | 0.0058 | 0.0670 | 0.0948 | 17.7795 | 0.0749 |
| sim | 4005 | left | pitch | swing | 4 | 0.0080 | 0.2082 | 0.3136 | 11.7200 | 0.2307 |
| sim | 4005 | left | pitch | touchdown | 4 | 0.0158 | 0.1375 | 0.2378 | 14.0674 | 0.2747 |
| sim | 4005 | left | roll | swing | 4 | 0.0052 | 0.1472 | 0.2259 | 11.7200 | 0.1465 |
| sim | 4005 | left | roll | touchdown | 4 | 0.0114 | 0.1786 | 0.2142 | 21.6232 | 0.1847 |
| sim | 4005 | right | pitch | swing | 4 | 0.0061 | 0.2285 | 0.3037 | 7.8133 | 0.2543 |
| sim | 4005 | right | pitch | touchdown | 4 | 0.0146 | 0.1329 | 0.2108 | 12.7944 | 0.2564 |
| sim | 4005 | right | roll | swing | 4 | 0.0035 | 0.0428 | 0.1044 | 14.8453 | 0.0998 |
| sim | 4005 | right | roll | touchdown | 4 | 0.0035 | 0.0344 | 0.0542 | 17.7766 | 0.0743 |
| sim | 5008 | left | pitch | swing | 4 | 0.0102 | 0.1995 | 0.3293 | 9.3314 | 0.1916 |
| sim | 5008 | left | pitch | touchdown | 4 | 0.0168 | 0.1610 | 0.2525 | 14.9944 | 0.2559 |
| sim | 5008 | left | roll | swing | 4 | 0.0064 | 0.1479 | 0.2443 | 17.9586 | 0.1483 |
| sim | 5008 | left | roll | touchdown | 4 | 0.0139 | 0.2333 | 0.2763 | 14.3441 | 0.1957 |
| sim | 5008 | right | pitch | swing | 4 | 0.0063 | 0.1543 | 0.2429 | 6.2309 | 0.2284 |
| sim | 5008 | right | pitch | touchdown | 4 | 0.0156 | 0.1286 | 0.2210 | 16.1302 | 0.1749 |
| sim | 5008 | right | roll | swing | 4 | 0.0024 | 0.0451 | 0.0720 | 10.9936 | 0.0844 |
| sim | 5008 | right | roll | touchdown | 4 | 0.0075 | 0.0668 | 0.0955 | 18.4477 | 0.0495 |

### Per-case Side Summary Analysis

- `real` 最大累计调整路径出现在 `35/0.5 all_ankles` / `left` / `roll` / `swing`，`joint path = 0.8582`。 这说明 real 的问题不是所有 case 平均一致，而是部分工况在局部窗口会出现明显更重的反复修正。
- `real` 最大兑现误差出现在 `30/0.4 all_ankles` / `left` / `roll` / `touchdown`，`track err = 0.3287`。 这说明某些 real case 不只是调得多，而且 `output -> joint` 落地更差。
- `real` 最大局部高频出现在 `35/0.5 all_ankles` / `right` / `roll` / `swing`，`joint hp = 0.0209`。 高频峰值并不总和最大路径、最大兑现误差落在同一行，再次说明不能只用 `hp_rms` 代表全部现象。
- `sim` 的对应峰值分别是：最大 `joint path` `0.3293`，最大 `track err` `0.3262`，最大 `joint hp` `0.0173`。 sim 也存在局部峰值，但总体仍低于 real 的 failure 级别窗口，说明 sim 的局部 realization 偏差尚未跨过可前走边界。
- 按 case 读，这批数据不支持“只有一个特定 `kp/kd` 工况坏掉”的说法。多个 real case 都能在不同侧、不同轴、不同窗口上拉高 `path/track err/hp`，更像系统性 sim2real 差异，而不是单一参数点异常。

## Interpretation

- roll swing: joint hp real/sim `0.0105` / `0.0033` = `3.2160`x; joint range `0.2364` / `0.0804` = `2.9415`x; joint path `0.4924` / `0.1263` = `3.8987`x; joint dir-rate `14.1360` / `12.0039` Hz = `1.1776`x; tracking err `0.1986` / `0.1252`.
- roll touchdown: joint hp real/sim `0.0135` / `0.0076` = `1.7630`x; joint range `0.2115` / `0.1016` = `2.0818`x; joint path `0.2966` / `0.1315` = `2.2553`x; joint dir-rate `15.2104` / `19.0338` Hz = `0.7991`x; tracking err `0.2136` / `0.1463`.
- pitch swing: joint hp real/sim `0.0095` / `0.0074` = `1.2837`x; joint range `0.2397` / `0.1676` = `1.4304`x; joint path `0.3956` / `0.2638` = `1.4996`x; joint dir-rate `8.3473` / `7.7281` Hz = `1.0801`x; tracking err `0.2321` / `0.2024`.
- pitch touchdown: joint hp real/sim `0.0106` / `0.0144` = `0.7371`x; joint range `0.2267` / `0.1344` = `1.6865`x; joint path `0.2587` / `0.2105` = `1.2289`x; joint dir-rate `8.5605` / `15.0551` Hz = `0.5686`x; tracking err `0.2630` / `0.2262`.
- 判定逻辑不再把 `jitter` 等同于单一高频残差：`hp_rms` 只回答局部高频抖动，`range/path_length` 回答调整幅值和总调整量，`direction_change_rate_hz/dominant_freq_hz` 回答调整频率。
- 如果 real 的 joint 指标显著高于 output 指标，说明抖动/调整主要在执行层、关节跟踪或结构响应中被引入或放大；如果 output 已经高，则需要回查策略输出或状态输入。
- Use the side summary to check whether the excess adjustment is left-right symmetric or concentrated on one ankle.
