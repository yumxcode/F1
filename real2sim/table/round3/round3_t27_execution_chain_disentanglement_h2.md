# 10 Execution Chain Disentanglement H2 on t27

## 口径

- 这份分析把 `pos_des_lpf -> pos` 当成当前可用的执行链代理量。
- 由于仓库里还没有补录 `/actuator_states`，当前不能把 `lpf -> actuator` 和 `actuator -> pos` 真正拆开，只能先做代理判定。
- 目标是判断：`sole_roll` 是否仍然主要跟随执行链，而不是即时 output。

## 摘要

| case | events | mean |sole_roll| | mean lpf->pos lag (ms) | mean pos->sole lag (ms) | H2 proxy support | dominant source |
|---|---:|---:|---:|---:|---:|---|
| 35/0.5 baseline | 4 | 1.6941 | 133.0428 | 0.0000 | 0.7500 | execution_chain_dominant |
| 50/0.8 right_roll | 4 | 1.7233 | 136.5278 | 18.5122 | 0.7500 | execution_chain_dominant |
| 40/0.8 right_roll | 4 | 1.6043 | 134.4351 | 71.8532 | 0.5000 | output_chain_dominant |
| 25/0.5 right_roll | 4 | 1.5744 | 141.8291 | 9.1503 | 1.0000 | execution_chain_dominant |
| 25/0.5 all_ankles | 4 | 1.6298 | 143.7665 | 16.4978 | 1.0000 | execution_chain_dominant |

## 解释

- 若 `lpf->pos` 代理滞后明显，而 `sole_roll` 仍主要判为 `execution_chain_dominant`，则 H2 代理成立。
- 这表示当前问题不是 output 直接把姿态做坏，而是目标到执行到位之间的响应迟滞在接触阶段占主导。
- 但这仍不是严格的 actuator-state 分解，因此只能作为 H2 的代理判定。

## 下一步

- 补录 `/actuator_states`，把 `lpf -> actuator` 与 `actuator -> pos` 真正拆开。
- 在同一批 kp 条件下重复前 4 步 touchdown，确认高 kp 下迟滞是否主要出现在执行链前段还是后段。
- 若补录后仍然保持左右镜像 `roll` 偏置，则继续往 `parallel_mapping / sign-convention / hard-ware degradation` 方向查。
