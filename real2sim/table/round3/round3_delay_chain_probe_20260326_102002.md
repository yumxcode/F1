# Delay Chain Probe

- Source action log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t25_action_20260326_102002.csv`
- Source joint log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t23_joint_20260326_102002.csv`
- Source current log: `/Users/yumx/code/X1/agibot_x1_infer/test_logs/data_csv/t3_current_20260326_102002.csv`
- Shared suffix: `20260326_102002`
- Joint sample dt: `10.000 ms`
- Action sample dt: `10.000 ms`
- Current sample dt: `10.000 ms`
- Max lag search window: `250 ms`

## Per-Joint Summary

| joint | group | action->target ms | target->pos ms | target->current ms | current->pos ms | target freq Hz | current freq Hz | pos freq Hz |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| left_ankle_pitch_joint | ankle | 0.0000 | 80.0018 | 20.0005 | 160.0037 | 1.4285 | 12.4997 | 1.4285 |
| left_ankle_roll_joint | ankle | 0.0000 | 60.0014 | 30.0007 | 70.0016 | 1.4285 | 1.4285 | 1.3889 |
| left_hip_pitch_joint | hip | 0.0000 | 160.0037 | 20.0005 | 0.0000 | 1.4285 | 1.4492 | 1.4084 |
| left_hip_roll_joint | hip | 0.0000 | 70.0016 | 30.0007 | 50.0011 | 1.4492 | 1.4706 | 12.4997 |
| left_hip_yaw_joint | hip | 0.0000 | 50.0011 | 20.0005 | 50.0011 | 1.4285 | 1.4706 | 12.4997 |
| left_knee_pitch_joint | knee | 0.0000 | 130.0030 | 20.0005 | 140.0032 | 1.4285 | 1.4492 | 1.4285 |
| right_ankle_pitch_joint | ankle | 0.0000 | 110.0025 | 20.0005 | 120.0027 | 1.4285 | 12.4997 | 1.4285 |
| right_ankle_roll_joint | ankle | 0.0000 | 50.0011 | 30.0007 | 60.0014 | 1.4285 | 1.4925 | 5.2630 |
| right_hip_pitch_joint | hip | 0.0000 | 180.0041 | 30.0007 | 140.0032 | 1.4285 | 1.4492 | 12.4997 |
| right_hip_roll_joint | hip | 0.0000 | 220.0050 | 30.0007 | 200.0046 | 1.4285 | 1.4492 | 1.4285 |
| right_hip_yaw_joint | hip | 0.0000 | 50.0011 | 20.0005 | 50.0011 | 1.4285 | 1.4492 | 12.4997 |
| right_knee_pitch_joint | knee | 0.0000 | 140.0032 | 20.0005 | 150.0034 | 1.4285 | 1.4285 | 1.4492 |

## Group Summary

| group | joint_count | mean action->target ms | mean target->pos ms | mean target->current ms | mean current->pos ms |
|---|---:|---:|---:|---:|---:|
| ankle | 4 | 0.0000 | 75.0017 | 25.0006 | 102.5023 |
| hip | 6 | 0.0000 | 121.6695 | 25.0006 | 81.6685 |
| knee | 2 | 0.0000 | 135.0031 | 20.0005 | 145.0033 |

## Interpretation

- `action->target` 主要看模型输出到关节目标的链路延迟。如果这里明显大于 0，优先查控制模块输出和记录时序。
- `target->current` 主要看关节目标到电机电流响应的延迟。如果这里大于 `action->target`，更像执行器/通信/驱动链问题。
- `current->pos` 主要看电机侧输出到实际关节位姿的机械响应。如果这里比 `target->current` 更慢，更像并联踝机械/接触/摩擦问题。
- `target->pos` 是总体现象，包含控制、驱动、机构三层延迟，适合和前两段一起看。
- `target/current/pos` 的 dominant freq 只作为节律参考，不作为主因；主因仍看各段 lag 是否在 ankle 上显著高于 knee/hip。
