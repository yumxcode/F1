# 05D FK Frame Definition Check

状态：`template`

用途：Phase 0 填写。未完成本表前，不允许把 FK `sole_roll` 当成真实脚底 roll 直接下结论。

| side | fk_body_name | mjcf_body_parent | fk_frame_claim | real_sole_plane_definition | contact_layer_definition | known_offset_or_unknown | phase1_required |
|---|---|---|---|---|---|---|---|
| left | link_left_ankle_roll | TBD | ankle_roll_link_body_frame | TBD | TBD | unknown | yes |
| right | link_right_ankle_roll | TBD | ankle_roll_link_body_frame | TBD | TBD | unknown | yes |

## 填写规则

- `fk_frame_claim` 在 Phase 1 通过前只能写 `ankle_roll_link_body_frame` 或等价保守描述。
- `real_sole_plane_definition` 需要说明真实脚底平面取哪几个点、哪块接触层或哪块底板作为参考。
- `contact_layer_definition` 需要说明实际接触地面的材料层、胶垫、鞋底或脚底板。
- `known_offset_or_unknown` 若没有实测，写 `unknown`，不要推断为 `zero`。
