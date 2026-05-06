# Round 3C Parallel Mapping Verification

## Scope

This report is the `05B` code-side verification for touchdown residual only. Swing dead-zone / small-signal realization has already been split out to `13_dead_zone_audit`.

## Side-by-Side Mapping Facts

| Item | Left ankle | Right ankle |
|---|---|---|
| `qm5` state source | `actr_right_.handle->state.position * actr_right_.direction` | `actr_left_.handle->state.position * actr_left_.direction` |
| `qm6` state source | `actr_left_.handle->state.position * actr_left_.direction` | `actr_right_.handle->state.position * actr_right_.direction` |
| extra `qm5 *= -1` | `True` | `False` |
| extra `qm6 *= -1` | `True` | `False` |
| extra `q6 *= -1` | `True` | `False` |
| `taum5` state source | `actr_right_.handle->state.effort * actr_right_.direction` | `actr_left_.handle->state.effort * actr_left_.direction` |
| `taum6` state source | `actr_left_.handle->state.effort * actr_left_.direction` | `actr_right_.handle->state.effort * actr_right_.direction` |
| `cqm5` phase | `qm5 + 1.2028` | `qm5 - 1.2028` |
| `cqm6` phase | `qm6 - 1.2030` | `qm6 + 1.2030` |
| `p_4p2_6_y` | `-0.025` | `0.025` |
| `p_4p4_6_y` | `0.025` | `-0.025` |
| `qm5Des` actuator target | `right` | `left` |
| `qm6Des` actuator target | `left` | `right` |
| `qm5Des` formula | `acos(c1 / sqrt(pow(a1, 2) + pow(b1, 2))) + atan(a1 / b1) - 1.2028` | `-acos(c1 / sqrt(pow(a1, 2) + pow(b1, 2))) + atan(a1 / b1) + 1.2028` |
| `qm6Des` formula | `-acos(c2 / sqrt(pow(a2, 2) + pow(b2, 2))) + atan(a2 / b2) + 1.2030` | `acos(c2 / sqrt(pow(a2, 2) + pow(b2, 2))) + atan(a2 / b2) - 1.2030` |
| pitch `kp` target | `right` | `left` |
| roll `kp` target | `left` | `right` |

## Verification Reading

- Actuator ownership is self-consistent: each side reads actuator state from the same actuator pair that later receives its pitch/roll command.
- The side-specific sign convention is asymmetric by construction: left applies an explicit `(qm5, qm6, q6)` flip bundle, while right relies on phase offsets and sign in the inverse formulas.
- Left/right cosine phase offsets are mirror-paired, not identical. This supports a deliberate mirrored convention rather than a copy-paste mistake.
- The geometric `y` offsets also mirror across sides. Mapping asymmetry therefore lives in a coupled sign package, not a single stray line.

## Residual Risks After 05B

- All mirrored conventions are hard-coded in C++, not configurable in YAML.
- There is no explicit code-level proof here that `TransformActuatorToJoint()` and `TransformJointToActuator()` are numerically inverse around touchdown operating points.
- Touchdown data still shows `bilateral_mirror_stable` roll residual after dead-zone screening, so code-level self-consistency does not eliminate geometry residual.

## Current 05B Conclusion

1. `05B` does not find a simple one-line left/right sign bug in actuator ownership. Pitch/roll actuator ownership is internally paired on both sides.
2. `05B` confirms that left/right mapping is not symmetric in a trivial sense; it is encoded as a mirrored hard-coded sign/phase package inside `ankle_transmission.cc`.
3. Because touchdown residual still shows stable mirror roll bias after dead-zone screening, the remaining high-priority explanations are:
   - numerical mismatch between mirrored code package and real mechanism / table operating region
   - hardware-side realization asymmetry on top of this hard-coded mapping
   - foot-space / contact geometry residual not represented by joint-space alone
