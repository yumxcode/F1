# 32 Complete Swing / Support Frequency Tables

Source: same touchdown detector and first-6 touchdown events as 28 report, but windows are now complete gait phases rather than short touchdown-centered windows.

## Window Definition

- `complete_swing`: previous opposite-side touchdown -> current touchdown of the same leg. This is the completed swing phase of the landing leg.
- `complete_support`: current touchdown -> next opposite-side touchdown. This approximates the completed single-support phase for the touchdown leg using touchdown boundaries.
- Step 1 often has no previous opposite touchdown, so its `complete_swing` is skipped. If a later boundary is missing, that phase is also skipped and recorded in the skipped CSV.

## Metric Notes

- `target_direction_change_rate_hz` / `joint_direction_change_rate_hz`: sign-reversal rate of first differences.
- `target_dominant_freq_hz` / `joint_dominant_freq_hz`: FFT/PSD dominant frequency after demeaning and Hann-windowing each phase signal; DC is ignored.
- `target_extrema_rate_hz` / `joint_extrema_rate_hz`: local extrema rate after epsilon filtering.
- `target_path_rate_radps` / `joint_path_rate_radps`: cumulative absolute motion per second.
- `target_range_rad` / `joint_range_rad`: max-min amplitude across the full phase window.
- `tracking_err_rms_rad`: RMS of `pos_des_raw - joint_pos` in the full phase window.

## Overview

| dataset | phase | role | joint | curves | duration | target dominant hz | joint dominant hz | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| real | complete_support | support_leg | ankle_pitch | 24 | 0.312 | 3.240 | 3.492 | 15.677 | 7.622 | 13.797 | 5.079 | 3.587 | 1.106 | 0.4088 | 0.2198 | 0.3577 |
| real | complete_support | support_leg | ankle_roll | 24 | 0.312 | 3.547 | 3.657 | 30.040 | 13.808 | 29.740 | 11.814 | 4.990 | 1.649 | 0.6428 | 0.2355 | 0.2519 |
| real | complete_support | support_leg | hip_pitch | 24 | 0.312 | 4.763 | 3.517 | 44.834 | 3.076 | 44.834 | 1.687 | 14.871 | 1.220 | 1.3760 | 0.2901 | 0.4464 |
| real | complete_support | support_leg | hip_roll | 24 | 0.312 | 3.756 | 3.398 | 26.921 | 9.136 | 23.599 | 5.082 | 12.551 | 0.527 | 1.4627 | 0.1196 | 0.6358 |
| real | complete_support | support_leg | knee_pitch | 24 | 0.312 | 3.524 | 3.398 | 34.777 | 3.032 | 34.207 | 1.779 | 5.348 | 1.650 | 0.7906 | 0.3684 | 0.2350 |
| real | complete_swing | swing_leg | ankle_pitch | 20 | 0.311 | 4.251 | 3.248 | 28.260 | 7.128 | 25.632 | 5.310 | 3.306 | 1.993 | 0.3787 | 0.4093 | 0.1888 |
| real | complete_swing | swing_leg | ankle_roll | 20 | 0.311 | 3.984 | 4.010 | 32.223 | 9.616 | 31.133 | 8.934 | 3.629 | 2.564 | 0.4944 | 0.3242 | 0.1680 |
| real | complete_swing | swing_leg | hip_pitch | 20 | 0.311 | 3.698 | 3.457 | 38.210 | 4.834 | 38.088 | 3.483 | 11.424 | 1.192 | 1.1580 | 0.2700 | 0.3868 |
| real | complete_swing | swing_leg | hip_roll | 20 | 0.311 | 3.635 | 3.457 | 32.503 | 8.397 | 29.312 | 4.021 | 8.604 | 0.279 | 1.2040 | 0.0599 | 0.3751 |
| real | complete_swing | swing_leg | knee_pitch | 20 | 0.311 | 3.457 | 3.457 | 29.905 | 2.695 | 29.688 | 2.533 | 6.045 | 4.045 | 0.9391 | 0.7988 | 0.4903 |
| sim | complete_support | support_leg | ankle_pitch | 24 | 0.370 | 3.126 | 3.271 | 17.639 | 10.318 | 14.368 | 9.298 | 3.807 | 0.929 | 0.7259 | 0.1520 | 0.3666 |
| sim | complete_support | support_leg | ankle_roll | 24 | 0.370 | 2.778 | 2.905 | 24.417 | 12.524 | 21.868 | 8.752 | 1.720 | 0.786 | 0.4093 | 0.1596 | 0.1742 |
| sim | complete_support | support_leg | hip_pitch | 24 | 0.370 | 2.778 | 2.778 | 31.463 | 3.227 | 31.098 | 2.168 | 4.360 | 1.151 | 0.7985 | 0.2598 | 0.2739 |
| sim | complete_support | support_leg | hip_roll | 24 | 0.370 | 2.778 | 2.778 | 22.544 | 6.032 | 19.203 | 3.796 | 5.321 | 0.612 | 0.9558 | 0.1270 | 0.3840 |
| sim | complete_support | support_leg | knee_pitch | 24 | 0.370 | 2.778 | 2.778 | 13.432 | 4.286 | 13.075 | 1.468 | 4.418 | 1.379 | 1.0389 | 0.4484 | 0.2718 |
| sim | complete_swing | swing_leg | ankle_pitch | 19 | 0.343 | 4.107 | 3.172 | 20.800 | 7.696 | 18.972 | 7.086 | 2.876 | 1.136 | 0.4320 | 0.2238 | 0.1796 |
| sim | complete_swing | swing_leg | ankle_roll | 19 | 0.343 | 3.164 | 3.636 | 27.713 | 14.034 | 26.141 | 7.929 | 2.295 | 0.432 | 0.4119 | 0.0851 | 0.1413 |
| sim | complete_swing | swing_leg | hip_pitch | 19 | 0.343 | 6.155 | 2.880 | 23.624 | 3.560 | 23.208 | 1.571 | 5.143 | 0.824 | 0.6701 | 0.1995 | 0.1907 |
| sim | complete_swing | swing_leg | hip_roll | 19 | 0.343 | 2.880 | 2.880 | 28.461 | 8.605 | 25.903 | 5.372 | 8.877 | 0.501 | 1.6183 | 0.0996 | 0.6103 |
| sim | complete_swing | swing_leg | knee_pitch | 19 | 0.343 | 2.880 | 2.880 | 20.699 | 7.534 | 20.241 | 6.131 | 2.963 | 1.403 | 0.6504 | 0.4101 | 0.2609 |

## By KP/KD

| kp_case | dataset | phase | role | joint | curves | duration | target dominant hz | joint dominant hz | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| kp25_kd0.4 | real | complete_support | support_leg | ankle_pitch | 6 | 0.320 | 2.577 | 3.559 | 24.308 | 8.508 | 21.947 | 6.270 | 4.072 | 1.069 | 0.4341 | 0.2340 | 0.3474 |
| kp25_kd0.4 | real | complete_support | support_leg | ankle_roll | 6 | 0.320 | 3.767 | 3.767 | 30.165 | 16.635 | 29.702 | 14.558 | 4.816 | 1.231 | 0.6531 | 0.1819 | 0.2777 |
| kp25_kd0.4 | real | complete_support | support_leg | hip_pitch | 6 | 0.320 | 6.201 | 3.648 | 49.724 | 3.772 | 49.724 | 1.901 | 15.115 | 0.972 | 1.2150 | 0.2300 | 0.3740 |
| kp25_kd0.4 | real | complete_support | support_leg | hip_roll | 6 | 0.320 | 4.272 | 3.172 | 29.940 | 10.944 | 25.498 | 8.120 | 12.804 | 0.448 | 1.5193 | 0.0996 | 0.5958 |
| kp25_kd0.4 | real | complete_support | support_leg | knee_pitch | 6 | 0.320 | 3.172 | 3.172 | 41.123 | 4.262 | 39.591 | 1.504 | 5.340 | 1.480 | 0.8613 | 0.3263 | 0.2359 |
| kp25_kd0.4 | real | complete_swing | swing_leg | ankle_pitch | 5 | 0.320 | 4.823 | 3.200 | 30.583 | 6.362 | 26.053 | 3.789 | 3.694 | 2.094 | 0.3107 | 0.4675 | 0.1766 |
| kp25_kd0.4 | real | complete_swing | swing_leg | ankle_roll | 5 | 0.320 | 3.200 | 3.741 | 36.516 | 11.818 | 35.451 | 11.262 | 4.240 | 1.861 | 0.5597 | 0.2763 | 0.1635 |
| kp25_kd0.4 | real | complete_swing | swing_leg | hip_pitch | 5 | 0.320 | 3.200 | 3.200 | 38.110 | 4.821 | 38.110 | 3.313 | 10.422 | 1.110 | 1.0189 | 0.2291 | 0.3130 |
| kp25_kd0.4 | real | complete_swing | swing_leg | hip_roll | 5 | 0.320 | 3.914 | 3.200 | 34.519 | 7.494 | 31.206 | 2.857 | 9.571 | 0.276 | 1.3988 | 0.0626 | 0.4895 |
| kp25_kd0.4 | real | complete_swing | swing_leg | knee_pitch | 5 | 0.320 | 3.200 | 3.200 | 30.347 | 2.361 | 30.347 | 2.361 | 5.119 | 4.171 | 0.9229 | 0.8508 | 0.4840 |
| kp25_kd0.4 | sim | complete_support | support_leg | ankle_pitch | 6 | 0.440 | 2.657 | 2.836 | 18.961 | 8.907 | 16.079 | 8.444 | 3.912 | 0.872 | 0.7365 | 0.1751 | 0.3728 |
| kp25_kd0.4 | sim | complete_support | support_leg | ankle_roll | 6 | 0.440 | 2.657 | 3.162 | 25.867 | 10.490 | 23.597 | 7.127 | 1.942 | 0.560 | 0.4679 | 0.1126 | 0.2723 |
| kp25_kd0.4 | sim | complete_support | support_leg | hip_pitch | 6 | 0.440 | 2.657 | 2.657 | 29.981 | 4.206 | 29.460 | 2.723 | 4.566 | 0.999 | 0.7899 | 0.2320 | 0.2659 |
| kp25_kd0.4 | sim | complete_support | support_leg | hip_roll | 6 | 0.440 | 2.657 | 2.657 | 24.220 | 6.944 | 20.498 | 6.021 | 5.622 | 0.640 | 1.1971 | 0.1379 | 0.4359 |
| kp25_kd0.4 | sim | complete_support | support_leg | knee_pitch | 6 | 0.440 | 2.657 | 2.657 | 13.136 | 4.745 | 13.136 | 1.264 | 4.291 | 1.256 | 1.0859 | 0.4151 | 0.2570 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | ankle_pitch | 4 | 0.335 | 3.631 | 3.076 | 24.053 | 8.507 | 22.917 | 7.158 | 2.951 | 0.954 | 0.4065 | 0.1789 | 0.1691 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | ankle_roll | 4 | 0.335 | 3.076 | 5.103 | 22.806 | 9.793 | 20.549 | 5.666 | 2.393 | 0.344 | 0.4435 | 0.0549 | 0.1740 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | hip_pitch | 4 | 0.335 | 3.076 | 3.076 | 23.524 | 3.180 | 22.956 | 2.399 | 5.232 | 0.854 | 0.7183 | 0.1837 | 0.2001 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | hip_roll | 4 | 0.335 | 3.076 | 3.076 | 28.488 | 8.152 | 26.444 | 4.317 | 9.825 | 0.522 | 1.6627 | 0.1075 | 0.5769 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | knee_pitch | 4 | 0.335 | 3.076 | 3.076 | 20.936 | 6.487 | 20.936 | 5.792 | 3.568 | 1.532 | 0.7851 | 0.3941 | 0.2760 |
| kp30_kd0.4 | real | complete_support | support_leg | ankle_pitch | 6 | 0.313 | 2.952 | 3.508 | 15.427 | 8.628 | 13.616 | 5.153 | 3.239 | 1.098 | 0.3178 | 0.2476 | 0.3648 |
| kp30_kd0.4 | real | complete_support | support_leg | ankle_roll | 6 | 0.313 | 3.508 | 4.362 | 27.846 | 18.952 | 27.109 | 16.801 | 5.056 | 1.229 | 0.6344 | 0.1839 | 0.2385 |
| kp30_kd0.4 | real | complete_support | support_leg | hip_pitch | 6 | 0.313 | 4.897 | 3.508 | 45.582 | 2.530 | 45.582 | 2.530 | 15.770 | 1.390 | 1.4488 | 0.3191 | 0.4707 |
| kp30_kd0.4 | real | complete_support | support_leg | hip_roll | 6 | 0.313 | 3.841 | 3.508 | 30.905 | 10.005 | 27.451 | 5.464 | 12.234 | 0.395 | 1.3786 | 0.0900 | 0.5853 |
| kp30_kd0.4 | real | complete_support | support_leg | knee_pitch | 6 | 0.313 | 3.508 | 3.508 | 33.185 | 2.775 | 32.845 | 2.200 | 5.377 | 1.919 | 0.7536 | 0.4544 | 0.2410 |
| kp30_kd0.4 | real | complete_swing | swing_leg | ankle_pitch | 5 | 0.314 | 4.651 | 3.584 | 27.050 | 5.788 | 25.046 | 3.570 | 3.581 | 2.432 | 0.3596 | 0.4876 | 0.2132 |
| kp30_kd0.4 | real | complete_swing | swing_leg | ankle_roll | 5 | 0.314 | 4.584 | 3.984 | 33.099 | 8.427 | 30.949 | 6.899 | 4.289 | 1.965 | 0.4853 | 0.2890 | 0.1543 |
| kp30_kd0.4 | real | complete_swing | swing_leg | hip_pitch | 5 | 0.314 | 4.049 | 3.584 | 42.772 | 5.098 | 42.772 | 2.753 | 10.637 | 1.139 | 0.9657 | 0.2832 | 0.3614 |
| kp30_kd0.4 | real | complete_swing | swing_leg | hip_roll | 5 | 0.314 | 3.584 | 3.584 | 35.342 | 6.549 | 32.408 | 3.443 | 10.560 | 0.291 | 1.3784 | 0.0614 | 0.4197 |
| kp30_kd0.4 | real | complete_swing | swing_leg | knee_pitch | 5 | 0.314 | 3.584 | 3.584 | 36.167 | 2.459 | 36.167 | 2.459 | 6.937 | 4.047 | 0.8697 | 0.8647 | 0.4565 |
| kp35_kd0.5 | real | complete_support | support_leg | ankle_pitch | 6 | 0.298 | 3.626 | 3.092 | 8.228 | 4.513 | 7.266 | 2.933 | 2.944 | 0.629 | 0.4203 | 0.1404 | 0.3820 |
| kp35_kd0.5 | real | complete_support | support_leg | ankle_roll | 6 | 0.298 | 3.610 | 3.196 | 27.513 | 6.553 | 27.513 | 4.863 | 5.016 | 1.380 | 0.6267 | 0.1839 | 0.2419 |
| kp35_kd0.5 | real | complete_support | support_leg | hip_pitch | 6 | 0.298 | 3.610 | 3.610 | 38.834 | 2.096 | 38.834 | 0.428 | 14.589 | 1.607 | 1.7223 | 0.4265 | 0.6060 |
| kp35_kd0.5 | real | complete_support | support_leg | hip_roll | 6 | 0.298 | 3.610 | 3.610 | 20.322 | 7.380 | 18.336 | 2.890 | 10.252 | 0.747 | 1.3964 | 0.1685 | 0.6740 |
| kp35_kd0.5 | real | complete_support | support_leg | knee_pitch | 6 | 0.298 | 3.610 | 3.610 | 31.305 | 2.226 | 30.899 | 0.965 | 5.268 | 1.536 | 0.7281 | 0.3548 | 0.2649 |
| kp35_kd0.5 | real | complete_swing | swing_leg | ankle_pitch | 5 | 0.298 | 3.686 | 2.853 | 23.286 | 4.113 | 21.773 | 2.133 | 2.676 | 1.782 | 0.4510 | 0.3722 | 0.2415 |
| kp35_kd0.5 | real | complete_swing | swing_leg | ankle_roll | 5 | 0.298 | 3.686 | 2.853 | 26.579 | 6.093 | 25.934 | 5.448 | 3.620 | 2.170 | 0.5391 | 0.3006 | 0.1926 |
| kp35_kd0.5 | real | complete_swing | swing_leg | hip_pitch | 5 | 0.298 | 4.187 | 3.686 | 33.822 | 3.851 | 33.334 | 3.338 | 12.544 | 1.701 | 1.5213 | 0.3965 | 0.5551 |
| kp35_kd0.5 | real | complete_swing | swing_leg | hip_roll | 5 | 0.298 | 3.686 | 3.686 | 29.804 | 9.656 | 26.598 | 4.652 | 7.106 | 0.349 | 1.0913 | 0.0632 | 0.3616 |
| kp35_kd0.5 | real | complete_swing | swing_leg | knee_pitch | 5 | 0.298 | 3.686 | 3.686 | 19.143 | 3.648 | 18.273 | 3.003 | 6.297 | 4.006 | 0.9462 | 0.7509 | 0.5784 |
| kp35_kd0.5 | sim | complete_support | support_leg | ankle_pitch | 6 | 0.342 | 3.323 | 2.860 | 20.379 | 10.300 | 17.448 | 8.045 | 3.647 | 0.884 | 0.6981 | 0.1488 | 0.3698 |
| kp35_kd0.5 | sim | complete_support | support_leg | ankle_roll | 6 | 0.342 | 2.860 | 2.860 | 21.816 | 12.839 | 18.518 | 9.791 | 1.646 | 0.750 | 0.3923 | 0.1448 | 0.1627 |
| kp35_kd0.5 | sim | complete_support | support_leg | hip_pitch | 6 | 0.342 | 2.860 | 2.860 | 31.110 | 2.944 | 31.110 | 1.567 | 4.470 | 1.196 | 0.8076 | 0.2560 | 0.2886 |
| kp35_kd0.5 | sim | complete_support | support_leg | hip_roll | 6 | 0.342 | 2.860 | 2.860 | 21.744 | 5.522 | 18.323 | 2.433 | 5.110 | 0.630 | 0.8865 | 0.1261 | 0.3661 |
| kp35_kd0.5 | sim | complete_support | support_leg | knee_pitch | 6 | 0.342 | 2.860 | 2.860 | 13.479 | 3.846 | 12.989 | 0.902 | 4.494 | 1.429 | 1.0224 | 0.4587 | 0.2795 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | ankle_pitch | 5 | 0.342 | 4.717 | 3.971 | 15.637 | 7.824 | 13.843 | 7.157 | 2.661 | 1.154 | 0.4415 | 0.2252 | 0.1953 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | ankle_roll | 5 | 0.342 | 2.860 | 3.505 | 29.667 | 14.454 | 29.000 | 8.222 | 2.282 | 0.378 | 0.4195 | 0.0671 | 0.1467 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | hip_pitch | 5 | 0.342 | 6.618 | 2.860 | 23.490 | 4.088 | 22.919 | 2.365 | 5.023 | 0.848 | 0.6606 | 0.2036 | 0.1964 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | hip_roll | 5 | 0.342 | 2.860 | 2.860 | 26.828 | 9.406 | 23.928 | 6.532 | 8.777 | 0.509 | 1.6113 | 0.0962 | 0.6285 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | knee_pitch | 5 | 0.342 | 2.860 | 2.860 | 18.573 | 9.135 | 17.948 | 7.387 | 2.951 | 1.352 | 0.6277 | 0.4005 | 0.2590 |
| kp40_kd0.5 | sim | complete_support | support_leg | ankle_pitch | 6 | 0.348 | 3.274 | 3.236 | 15.543 | 11.068 | 12.214 | 10.617 | 3.891 | 0.923 | 0.7410 | 0.1378 | 0.3638 |
| kp40_kd0.5 | sim | complete_support | support_leg | ankle_roll | 6 | 0.348 | 2.798 | 2.798 | 26.159 | 13.411 | 23.365 | 8.074 | 1.642 | 0.962 | 0.4006 | 0.1861 | 0.1499 |
| kp40_kd0.5 | sim | complete_support | support_leg | hip_pitch | 6 | 0.348 | 2.798 | 2.798 | 32.095 | 2.878 | 31.619 | 2.428 | 4.247 | 1.205 | 0.8019 | 0.2699 | 0.2682 |
| kp40_kd0.5 | sim | complete_support | support_leg | hip_roll | 6 | 0.348 | 2.798 | 2.798 | 23.320 | 5.852 | 20.441 | 3.399 | 5.430 | 0.594 | 0.8752 | 0.1178 | 0.3770 |
| kp40_kd0.5 | sim | complete_support | support_leg | knee_pitch | 6 | 0.348 | 2.798 | 2.798 | 15.468 | 4.270 | 14.978 | 1.842 | 4.387 | 1.413 | 1.0278 | 0.4597 | 0.2729 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | ankle_pitch | 5 | 0.350 | 3.392 | 2.786 | 20.462 | 7.536 | 19.265 | 6.965 | 2.774 | 1.180 | 0.4391 | 0.2497 | 0.1814 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | ankle_roll | 5 | 0.350 | 2.786 | 3.392 | 30.651 | 14.849 | 28.945 | 8.074 | 2.426 | 0.388 | 0.4140 | 0.0781 | 0.1358 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | hip_pitch | 5 | 0.350 | 7.658 | 2.786 | 25.207 | 2.866 | 25.207 | 1.129 | 5.302 | 0.782 | 0.6664 | 0.1954 | 0.1842 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | hip_roll | 5 | 0.350 | 2.786 | 2.786 | 27.121 | 8.597 | 24.303 | 5.731 | 8.755 | 0.499 | 1.6483 | 0.0995 | 0.6123 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | knee_pitch | 5 | 0.350 | 2.786 | 2.786 | 22.872 | 7.353 | 22.331 | 5.562 | 2.693 | 1.386 | 0.6314 | 0.4301 | 0.2581 |
| kp40_kd0.8 | real | complete_support | support_leg | ankle_pitch | 6 | 0.315 | 3.807 | 3.807 | 14.745 | 8.841 | 12.360 | 5.961 | 4.094 | 1.629 | 0.4630 | 0.2573 | 0.3368 |
| kp40_kd0.8 | real | complete_support | support_leg | ankle_roll | 6 | 0.315 | 3.302 | 3.302 | 34.636 | 13.092 | 34.636 | 11.036 | 5.070 | 2.757 | 0.6568 | 0.3923 | 0.2495 |
| kp40_kd0.8 | real | complete_support | support_leg | hip_pitch | 6 | 0.315 | 4.344 | 3.302 | 45.196 | 3.905 | 45.196 | 1.892 | 14.008 | 0.909 | 1.1180 | 0.1848 | 0.3348 |
| kp40_kd0.8 | real | complete_support | support_leg | hip_roll | 6 | 0.315 | 3.302 | 3.302 | 26.515 | 8.216 | 23.113 | 3.855 | 14.913 | 0.519 | 1.5565 | 0.1202 | 0.6881 |
| kp40_kd0.8 | real | complete_support | support_leg | knee_pitch | 6 | 0.315 | 3.807 | 3.302 | 33.494 | 2.863 | 33.494 | 2.447 | 5.408 | 1.664 | 0.8196 | 0.3382 | 0.1982 |
| kp40_kd0.8 | real | complete_swing | swing_leg | ankle_pitch | 5 | 0.314 | 3.844 | 3.356 | 32.123 | 12.249 | 29.656 | 11.749 | 3.273 | 1.662 | 0.3936 | 0.3097 | 0.1240 |
| kp40_kd0.8 | real | complete_swing | swing_leg | ankle_roll | 5 | 0.314 | 4.467 | 5.464 | 32.697 | 12.126 | 32.197 | 12.126 | 2.368 | 4.261 | 0.3934 | 0.4310 | 0.1618 |
| kp40_kd0.8 | real | complete_swing | swing_leg | hip_pitch | 5 | 0.314 | 3.356 | 3.356 | 38.135 | 5.567 | 38.135 | 4.527 | 12.093 | 0.818 | 1.1260 | 0.1714 | 0.3177 |
| kp40_kd0.8 | real | complete_swing | swing_leg | hip_roll | 5 | 0.314 | 3.356 | 3.356 | 30.346 | 9.889 | 27.036 | 5.132 | 7.179 | 0.198 | 0.9474 | 0.0523 | 0.2294 |
| kp40_kd0.8 | real | complete_swing | swing_leg | knee_pitch | 5 | 0.314 | 3.356 | 3.356 | 33.964 | 2.311 | 33.964 | 2.311 | 5.825 | 3.956 | 1.0177 | 0.7288 | 0.4423 |
| kp50_kd0.8 | sim | complete_support | support_leg | ankle_pitch | 6 | 0.349 | 3.250 | 4.151 | 15.673 | 10.996 | 11.732 | 10.087 | 3.778 | 1.038 | 0.7283 | 0.1464 | 0.3600 |
| kp50_kd0.8 | sim | complete_support | support_leg | ankle_roll | 6 | 0.349 | 2.799 | 2.799 | 23.825 | 13.358 | 21.992 | 10.014 | 1.650 | 0.872 | 0.3764 | 0.1951 | 0.1117 |
| kp50_kd0.8 | sim | complete_support | support_leg | hip_pitch | 6 | 0.349 | 2.799 | 2.799 | 32.665 | 2.881 | 32.202 | 1.955 | 4.156 | 1.204 | 0.7944 | 0.2811 | 0.2727 |
| kp50_kd0.8 | sim | complete_support | support_leg | hip_roll | 6 | 0.349 | 2.799 | 2.799 | 20.892 | 5.811 | 17.549 | 3.330 | 5.120 | 0.583 | 0.8645 | 0.1262 | 0.3572 |
| kp50_kd0.8 | sim | complete_support | support_leg | knee_pitch | 6 | 0.349 | 2.799 | 2.799 | 11.645 | 4.283 | 11.199 | 1.865 | 4.499 | 1.417 | 1.0194 | 0.4598 | 0.2777 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | ankle_pitch | 5 | 0.344 | 4.594 | 2.837 | 23.699 | 7.080 | 20.651 | 7.080 | 3.132 | 1.218 | 0.4359 | 0.2324 | 0.1705 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | ankle_roll | 5 | 0.344 | 3.918 | 2.837 | 26.746 | 16.191 | 24.953 | 9.302 | 2.098 | 0.600 | 0.3771 | 0.1344 | 0.1153 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | hip_pitch | 5 | 0.344 | 6.651 | 2.837 | 22.254 | 4.032 | 21.699 | 0.556 | 5.032 | 0.818 | 0.6446 | 0.2120 | 0.1842 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | hip_roll | 5 | 0.344 | 2.837 | 2.837 | 31.413 | 8.175 | 29.048 | 4.699 | 8.341 | 0.476 | 1.5598 | 0.0968 | 0.6168 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | knee_pitch | 5 | 0.344 | 2.837 | 2.837 | 20.461 | 6.952 | 19.889 | 5.714 | 2.762 | 1.368 | 0.5842 | 0.4124 | 0.2534 |

## By KP/KD And Left/Right Side

| kp_case | dataset | phase | role | side | joint | curves | duration | target dominant hz | joint dominant hz | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| kp25_kd0.4 | real | complete_support | support_leg | left | ankle_pitch | 3 | 0.330 | 3.191 | 3.967 | 23.014 | 5.953 | 21.294 | 3.439 | 3.391 | 1.365 | 0.3732 | 0.3167 | 0.3343 |
| kp25_kd0.4 | real | complete_support | support_leg | left | ankle_roll | 3 | 0.330 | 3.191 | 3.191 | 26.852 | 11.643 | 25.926 | 8.468 | 3.775 | 1.601 | 0.6482 | 0.2542 | 0.3046 |
| kp25_kd0.4 | real | complete_support | support_leg | left | hip_pitch | 3 | 0.330 | 9.250 | 3.191 | 42.199 | 3.307 | 42.199 | 1.587 | 15.638 | 1.380 | 1.2906 | 0.3475 | 0.4777 |
| kp25_kd0.4 | real | complete_support | support_leg | left | hip_roll | 3 | 0.330 | 3.191 | 3.191 | 27.383 | 12.568 | 21.562 | 9.922 | 11.755 | 0.491 | 1.3672 | 0.1118 | 0.4990 |
| kp25_kd0.4 | real | complete_support | support_leg | left | knee_pitch | 3 | 0.330 | 3.191 | 3.191 | 37.172 | 3.308 | 37.172 | 0.794 | 5.890 | 1.854 | 1.0150 | 0.4431 | 0.2899 |
| kp25_kd0.4 | real | complete_support | support_leg | right | ankle_pitch | 3 | 0.310 | 1.962 | 3.152 | 25.602 | 11.062 | 22.600 | 9.101 | 4.754 | 0.774 | 0.4949 | 0.1513 | 0.3604 |
| kp25_kd0.4 | real | complete_support | support_leg | right | ankle_roll | 3 | 0.310 | 4.342 | 4.342 | 33.478 | 21.628 | 33.478 | 20.648 | 5.857 | 0.861 | 0.6580 | 0.1097 | 0.2508 |
| kp25_kd0.4 | real | complete_support | support_leg | right | hip_pitch | 3 | 0.310 | 3.152 | 4.105 | 57.248 | 4.236 | 57.248 | 2.215 | 14.591 | 0.563 | 1.1395 | 0.1126 | 0.2703 |
| kp25_kd0.4 | real | complete_support | support_leg | right | hip_roll | 3 | 0.310 | 5.352 | 3.152 | 32.497 | 9.320 | 29.435 | 6.318 | 13.854 | 0.404 | 1.6713 | 0.0873 | 0.6926 |
| kp25_kd0.4 | real | complete_support | support_leg | right | knee_pitch | 3 | 0.310 | 3.152 | 3.152 | 45.073 | 5.217 | 42.011 | 2.215 | 4.790 | 1.107 | 0.7076 | 0.2095 | 0.1818 |
| kp25_kd0.4 | real | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.305 | 4.999 | 3.214 | 35.781 | 4.793 | 30.608 | 3.322 | 2.480 | 2.040 | 0.2676 | 0.4034 | 0.1538 |
| kp25_kd0.4 | real | complete_swing | swing_leg | left | ankle_roll | 2 | 0.305 | 3.214 | 3.214 | 33.549 | 8.115 | 32.078 | 8.115 | 2.114 | 2.694 | 0.3642 | 0.4138 | 0.2080 |
| kp25_kd0.4 | real | complete_swing | swing_leg | left | hip_pitch | 2 | 0.305 | 3.214 | 3.214 | 44.277 | 3.322 | 44.277 | 3.322 | 7.772 | 1.318 | 0.9736 | 0.2598 | 0.2978 |
| kp25_kd0.4 | real | complete_swing | swing_leg | left | hip_roll | 2 | 0.305 | 4.999 | 3.214 | 37.685 | 1.471 | 34.363 | 0.000 | 6.203 | 0.315 | 0.9470 | 0.0879 | 0.2994 |
| kp25_kd0.4 | real | complete_swing | swing_leg | left | knee_pitch | 2 | 0.305 | 3.214 | 3.214 | 22.493 | 3.322 | 22.493 | 3.322 | 4.978 | 3.893 | 0.9722 | 0.7492 | 0.4426 |
| kp25_kd0.4 | real | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.330 | 4.706 | 3.191 | 27.118 | 7.408 | 23.017 | 4.101 | 4.504 | 2.130 | 0.3394 | 0.5102 | 0.1918 |
| kp25_kd0.4 | real | complete_swing | swing_leg | right | ankle_roll | 3 | 0.330 | 3.191 | 4.092 | 38.494 | 14.287 | 37.700 | 13.361 | 5.657 | 1.305 | 0.6901 | 0.1847 | 0.1338 |
| kp25_kd0.4 | real | complete_swing | swing_leg | right | hip_pitch | 3 | 0.330 | 3.191 | 3.191 | 33.999 | 5.821 | 33.999 | 3.307 | 12.188 | 0.971 | 1.0492 | 0.2086 | 0.3232 |
| kp25_kd0.4 | real | complete_swing | swing_leg | right | hip_roll | 3 | 0.330 | 3.191 | 3.191 | 32.409 | 11.510 | 29.102 | 4.762 | 11.817 | 0.251 | 1.7000 | 0.0458 | 0.6162 |
| kp25_kd0.4 | real | complete_swing | swing_leg | right | knee_pitch | 3 | 0.330 | 3.191 | 3.191 | 35.583 | 1.720 | 35.583 | 1.720 | 5.213 | 4.357 | 0.8900 | 0.9186 | 0.5117 |
| kp25_kd0.4 | sim | complete_support | support_leg | left | ankle_pitch | 4 | 0.470 | 2.672 | 2.941 | 16.297 | 9.313 | 14.672 | 8.618 | 4.129 | 0.922 | 0.7247 | 0.1804 | 0.3599 |
| kp25_kd0.4 | sim | complete_support | support_leg | left | ankle_roll | 4 | 0.470 | 2.672 | 2.672 | 25.164 | 10.550 | 21.759 | 7.210 | 1.924 | 0.655 | 0.5085 | 0.1411 | 0.2969 |
| kp25_kd0.4 | sim | complete_support | support_leg | left | hip_pitch | 4 | 0.470 | 2.672 | 2.672 | 30.909 | 4.391 | 30.909 | 2.168 | 4.264 | 0.793 | 0.6881 | 0.2151 | 0.2143 |
| kp25_kd0.4 | sim | complete_support | support_leg | left | hip_roll | 4 | 0.470 | 2.672 | 2.672 | 25.606 | 5.799 | 21.373 | 4.984 | 5.319 | 0.625 | 1.1289 | 0.1385 | 0.4282 |
| kp25_kd0.4 | sim | complete_support | support_leg | left | knee_pitch | 4 | 0.470 | 2.672 | 2.672 | 13.382 | 5.200 | 13.382 | 1.896 | 4.466 | 1.258 | 1.1237 | 0.4205 | 0.2449 |
| kp25_kd0.4 | sim | complete_support | support_leg | right | ankle_pitch | 2 | 0.380 | 2.626 | 2.626 | 24.290 | 8.097 | 18.892 | 8.097 | 3.478 | 0.772 | 0.7600 | 0.1644 | 0.3985 |
| kp25_kd0.4 | sim | complete_support | support_leg | right | ankle_roll | 2 | 0.380 | 2.626 | 4.141 | 27.273 | 10.369 | 27.273 | 6.960 | 1.978 | 0.369 | 0.3867 | 0.0556 | 0.2231 |
| kp25_kd0.4 | sim | complete_support | support_leg | right | hip_pitch | 2 | 0.380 | 2.626 | 2.626 | 28.125 | 3.835 | 26.563 | 3.835 | 5.169 | 1.409 | 0.9933 | 0.2658 | 0.3693 |
| kp25_kd0.4 | sim | complete_support | support_leg | right | hip_roll | 2 | 0.380 | 2.626 | 2.626 | 21.449 | 9.233 | 18.750 | 8.097 | 6.227 | 0.670 | 1.3334 | 0.1367 | 0.4513 |
| kp25_kd0.4 | sim | complete_support | support_leg | right | knee_pitch | 2 | 0.380 | 2.626 | 2.626 | 12.642 | 3.835 | 12.642 | 0.000 | 3.941 | 1.253 | 1.0104 | 0.4045 | 0.2812 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.380 | 3.737 | 2.626 | 26.136 | 8.807 | 23.864 | 6.108 | 3.271 | 0.907 | 0.3617 | 0.1756 | 0.1133 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | left | ankle_roll | 2 | 0.380 | 2.626 | 2.626 | 20.739 | 10.369 | 17.614 | 7.670 | 1.920 | 0.316 | 0.4853 | 0.0665 | 0.2149 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | left | hip_pitch | 2 | 0.380 | 2.626 | 2.626 | 26.847 | 2.699 | 25.710 | 1.136 | 4.687 | 0.777 | 0.7616 | 0.1912 | 0.1888 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | left | hip_roll | 2 | 0.380 | 2.626 | 2.626 | 23.011 | 8.097 | 20.313 | 4.972 | 8.659 | 0.611 | 1.6287 | 0.1348 | 0.5440 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | left | knee_pitch | 2 | 0.380 | 2.626 | 2.626 | 21.165 | 6.534 | 21.165 | 6.534 | 3.754 | 1.800 | 0.9714 | 0.4673 | 0.3148 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | right | ankle_pitch | 2 | 0.290 | 3.525 | 3.525 | 21.970 | 8.207 | 21.970 | 8.207 | 2.632 | 1.001 | 0.4512 | 0.1822 | 0.2250 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | right | ankle_roll | 2 | 0.290 | 3.525 | 7.579 | 24.874 | 9.217 | 23.485 | 3.662 | 2.867 | 0.372 | 0.4018 | 0.0433 | 0.1331 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | right | hip_pitch | 2 | 0.290 | 3.525 | 3.525 | 20.202 | 3.662 | 20.202 | 3.662 | 5.777 | 0.932 | 0.6750 | 0.1762 | 0.2113 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | right | hip_roll | 2 | 0.290 | 3.525 | 3.525 | 33.965 | 8.207 | 32.576 | 3.662 | 10.990 | 0.433 | 1.6966 | 0.0801 | 0.6098 |
| kp25_kd0.4 | sim | complete_swing | swing_leg | right | knee_pitch | 2 | 0.290 | 3.525 | 3.525 | 20.707 | 6.439 | 20.707 | 5.050 | 3.383 | 1.264 | 0.5987 | 0.3210 | 0.2373 |
| kp30_kd0.4 | real | complete_support | support_leg | left | ankle_pitch | 3 | 0.263 | 4.195 | 4.195 | 16.173 | 9.689 | 13.627 | 6.251 | 4.175 | 1.169 | 0.3778 | 0.2440 | 0.3344 |
| kp30_kd0.4 | real | complete_support | support_leg | left | ankle_roll | 3 | 0.263 | 4.195 | 4.195 | 22.159 | 10.218 | 21.366 | 7.671 | 4.367 | 1.903 | 0.6456 | 0.2964 | 0.2752 |
| kp30_kd0.4 | real | complete_support | support_leg | left | hip_pitch | 3 | 0.263 | 5.861 | 4.195 | 40.911 | 0.793 | 40.911 | 0.793 | 18.707 | 1.819 | 1.5890 | 0.4250 | 0.5835 |
| kp30_kd0.4 | real | complete_support | support_leg | left | hip_roll | 3 | 0.263 | 4.195 | 4.195 | 28.773 | 10.218 | 24.374 | 3.967 | 10.917 | 0.436 | 1.1971 | 0.0986 | 0.4303 |
| kp30_kd0.4 | real | complete_support | support_leg | left | knee_pitch | 3 | 0.263 | 4.195 | 4.195 | 30.722 | 2.645 | 30.722 | 2.645 | 6.890 | 1.857 | 1.0146 | 0.4039 | 0.2799 |
| kp30_kd0.4 | real | complete_support | support_leg | right | ankle_pitch | 3 | 0.363 | 1.708 | 2.820 | 14.680 | 7.567 | 13.605 | 4.056 | 2.302 | 1.028 | 0.2578 | 0.2512 | 0.3951 |
| kp30_kd0.4 | real | complete_support | support_leg | right | ankle_roll | 3 | 0.363 | 2.820 | 4.528 | 33.533 | 27.687 | 32.853 | 25.932 | 5.746 | 0.554 | 0.6232 | 0.0714 | 0.2018 |
| kp30_kd0.4 | real | complete_support | support_leg | right | hip_pitch | 3 | 0.363 | 3.932 | 2.820 | 50.252 | 4.266 | 50.252 | 4.266 | 12.833 | 0.962 | 1.3086 | 0.2132 | 0.3579 |
| kp30_kd0.4 | real | complete_support | support_leg | right | hip_roll | 3 | 0.363 | 3.487 | 2.820 | 33.038 | 9.792 | 30.527 | 6.962 | 13.551 | 0.355 | 1.5601 | 0.0815 | 0.7404 |
| kp30_kd0.4 | real | complete_support | support_leg | right | knee_pitch | 3 | 0.363 | 2.820 | 2.820 | 35.649 | 2.906 | 34.969 | 1.755 | 3.864 | 1.981 | 0.4925 | 0.5048 | 0.2021 |
| kp30_kd0.4 | real | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.390 | 5.335 | 2.668 | 30.518 | 5.491 | 30.518 | 3.766 | 3.058 | 2.378 | 0.3438 | 0.4880 | 0.2100 |
| kp30_kd0.4 | real | complete_swing | swing_leg | left | ankle_roll | 2 | 0.390 | 2.668 | 3.668 | 41.426 | 5.491 | 38.681 | 5.491 | 2.315 | 2.914 | 0.3393 | 0.4499 | 0.2056 |
| kp30_kd0.4 | real | complete_swing | swing_leg | left | hip_pitch | 2 | 0.390 | 2.668 | 2.668 | 51.073 | 3.766 | 51.073 | 1.725 | 8.838 | 1.453 | 1.0322 | 0.4560 | 0.3453 |
| kp30_kd0.4 | real | complete_swing | swing_leg | left | hip_roll | 2 | 0.390 | 2.668 | 2.668 | 33.189 | 5.807 | 29.423 | 4.786 | 9.818 | 0.276 | 1.0765 | 0.0761 | 0.3485 |
| kp30_kd0.4 | real | complete_swing | swing_leg | left | knee_pitch | 2 | 0.390 | 2.668 | 2.668 | 34.210 | 3.766 | 34.210 | 3.766 | 6.408 | 3.662 | 1.0023 | 0.8670 | 0.4407 |
| kp30_kd0.4 | real | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.263 | 4.195 | 4.195 | 24.738 | 5.986 | 21.397 | 3.439 | 3.930 | 2.468 | 0.3701 | 0.4874 | 0.2154 |
| kp30_kd0.4 | real | complete_swing | swing_leg | right | ankle_roll | 3 | 0.263 | 5.861 | 4.195 | 27.548 | 10.384 | 25.795 | 7.838 | 5.605 | 1.332 | 0.5827 | 0.1818 | 0.1201 |
| kp30_kd0.4 | real | complete_swing | swing_leg | right | hip_pitch | 3 | 0.263 | 4.970 | 4.195 | 37.237 | 5.986 | 37.237 | 3.439 | 11.836 | 0.929 | 0.9213 | 0.1680 | 0.3720 |
| kp30_kd0.4 | real | complete_swing | swing_leg | right | hip_roll | 3 | 0.263 | 4.195 | 4.195 | 36.777 | 7.044 | 34.397 | 2.547 | 11.055 | 0.301 | 1.5797 | 0.0516 | 0.4672 |
| kp30_kd0.4 | real | complete_swing | swing_leg | right | knee_pitch | 3 | 0.263 | 4.195 | 4.195 | 37.473 | 1.587 | 37.473 | 1.587 | 7.290 | 4.304 | 0.7813 | 0.8632 | 0.4670 |
| kp35_kd0.5 | real | complete_support | support_leg | left | ankle_pitch | 3 | 0.257 | 4.309 | 5.143 | 8.546 | 7.950 | 8.546 | 4.790 | 3.263 | 0.800 | 0.4128 | 0.1504 | 0.3549 |
| kp35_kd0.5 | real | complete_support | support_leg | left | ankle_roll | 3 | 0.257 | 4.309 | 4.309 | 15.386 | 8.805 | 15.386 | 6.500 | 5.062 | 2.360 | 0.6718 | 0.3112 | 0.2227 |
| kp35_kd0.5 | real | complete_support | support_leg | left | hip_pitch | 3 | 0.257 | 4.309 | 4.309 | 33.847 | 2.305 | 33.847 | 0.855 | 12.192 | 1.534 | 1.3781 | 0.3241 | 0.5850 |
| kp35_kd0.5 | real | complete_support | support_leg | left | hip_roll | 3 | 0.257 | 4.309 | 4.309 | 20.096 | 9.060 | 16.935 | 3.080 | 8.944 | 0.622 | 1.2858 | 0.1214 | 0.6827 |
| kp35_kd0.5 | real | complete_support | support_leg | left | knee_pitch | 3 | 0.257 | 4.309 | 4.309 | 26.411 | 2.565 | 26.411 | 0.855 | 6.201 | 1.703 | 0.7986 | 0.3522 | 0.2816 |
| kp35_kd0.5 | real | complete_support | support_leg | right | ankle_pitch | 3 | 0.340 | 2.943 | 1.042 | 7.910 | 1.075 | 5.986 | 1.075 | 2.625 | 0.459 | 0.4278 | 0.1305 | 0.4092 |
| kp35_kd0.5 | real | complete_support | support_leg | right | ankle_roll | 3 | 0.340 | 2.910 | 2.083 | 39.640 | 4.300 | 39.640 | 3.225 | 4.970 | 0.401 | 0.5816 | 0.0566 | 0.2611 |
| kp35_kd0.5 | real | complete_support | support_leg | right | hip_pitch | 3 | 0.340 | 2.910 | 2.910 | 43.821 | 1.888 | 43.821 | 0.000 | 16.986 | 1.680 | 2.0664 | 0.5290 | 0.6270 |
| kp35_kd0.5 | real | complete_support | support_leg | right | hip_roll | 3 | 0.340 | 2.910 | 2.910 | 20.549 | 5.699 | 19.736 | 2.700 | 11.559 | 0.872 | 1.5069 | 0.2156 | 0.6653 |
| kp35_kd0.5 | real | complete_support | support_leg | right | knee_pitch | 3 | 0.340 | 2.910 | 2.910 | 36.198 | 1.888 | 35.386 | 1.075 | 4.335 | 1.369 | 0.6575 | 0.3575 | 0.2483 |
| kp35_kd0.5 | real | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.360 | 2.752 | 2.752 | 33.585 | 5.663 | 32.366 | 4.050 | 2.295 | 1.919 | 0.4752 | 0.4422 | 0.2063 |
| kp35_kd0.5 | real | complete_swing | swing_leg | left | ankle_roll | 2 | 0.360 | 2.752 | 2.752 | 26.703 | 7.276 | 25.090 | 5.663 | 1.943 | 2.957 | 0.4213 | 0.3937 | 0.2273 |
| kp35_kd0.5 | real | complete_swing | swing_leg | left | hip_pitch | 2 | 0.360 | 2.752 | 2.752 | 40.467 | 2.832 | 39.248 | 2.832 | 10.916 | 1.083 | 1.5057 | 0.3104 | 0.4277 |
| kp35_kd0.5 | real | complete_swing | swing_leg | left | hip_roll | 2 | 0.360 | 2.752 | 2.752 | 29.890 | 10.932 | 28.672 | 4.444 | 6.336 | 0.338 | 1.0376 | 0.0860 | 0.4100 |
| kp35_kd0.5 | real | complete_swing | swing_leg | left | knee_pitch | 2 | 0.360 | 2.752 | 2.752 | 28.747 | 5.663 | 28.747 | 4.050 | 6.200 | 3.136 | 0.8705 | 0.5995 | 0.3958 |
| kp35_kd0.5 | real | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.257 | 4.309 | 2.920 | 16.420 | 3.080 | 14.710 | 0.855 | 2.931 | 1.690 | 0.4350 | 0.3256 | 0.2650 |
| kp35_kd0.5 | real | complete_swing | swing_leg | right | ankle_roll | 3 | 0.257 | 4.309 | 2.920 | 26.497 | 5.305 | 26.497 | 5.305 | 4.738 | 1.646 | 0.6176 | 0.2384 | 0.1694 |
| kp35_kd0.5 | real | complete_swing | swing_leg | right | hip_pitch | 3 | 0.257 | 5.143 | 4.309 | 29.392 | 4.530 | 29.392 | 3.675 | 13.629 | 2.113 | 1.5317 | 0.4538 | 0.6400 |
| kp35_kd0.5 | real | complete_swing | swing_leg | right | hip_roll | 3 | 0.257 | 4.309 | 4.309 | 29.746 | 8.805 | 25.216 | 4.790 | 7.620 | 0.356 | 1.1271 | 0.0480 | 0.3294 |
| kp35_kd0.5 | real | complete_swing | swing_leg | right | knee_pitch | 3 | 0.257 | 4.309 | 4.309 | 12.740 | 2.305 | 11.290 | 2.305 | 6.361 | 4.586 | 0.9967 | 0.8519 | 0.7002 |
| kp35_kd0.5 | sim | complete_support | support_leg | left | ankle_pitch | 3 | 0.363 | 3.607 | 2.682 | 18.238 | 9.117 | 14.531 | 4.607 | 3.477 | 0.952 | 0.6406 | 0.1646 | 0.3303 |
| kp35_kd0.5 | sim | complete_support | support_leg | left | ankle_roll | 3 | 0.363 | 2.682 | 2.682 | 22.943 | 11.124 | 17.459 | 8.293 | 1.407 | 0.990 | 0.4416 | 0.2141 | 0.1591 |
| kp35_kd0.5 | sim | complete_support | support_leg | left | hip_pitch | 3 | 0.363 | 2.682 | 2.682 | 39.379 | 2.755 | 39.379 | 0.000 | 3.639 | 0.901 | 0.5940 | 0.2428 | 0.2071 |
| kp35_kd0.5 | sim | complete_support | support_leg | left | hip_roll | 3 | 0.363 | 2.682 | 2.682 | 24.751 | 2.755 | 21.043 | 1.803 | 4.870 | 0.734 | 0.8685 | 0.1494 | 0.3492 |
| kp35_kd0.5 | sim | complete_support | support_leg | left | knee_pitch | 3 | 0.363 | 2.682 | 2.682 | 13.777 | 4.559 | 13.777 | 1.803 | 4.380 | 1.419 | 1.0438 | 0.4969 | 0.2539 |
| kp35_kd0.5 | sim | complete_support | support_leg | right | ankle_pitch | 3 | 0.320 | 3.038 | 3.038 | 22.519 | 11.482 | 20.366 | 11.482 | 3.817 | 0.816 | 0.7556 | 0.1330 | 0.4093 |
| kp35_kd0.5 | sim | complete_support | support_leg | right | ankle_roll | 3 | 0.320 | 3.038 | 3.038 | 20.689 | 14.554 | 19.578 | 11.290 | 1.885 | 0.510 | 0.3430 | 0.0754 | 0.1664 |
| kp35_kd0.5 | sim | complete_support | support_leg | right | hip_pitch | 3 | 0.320 | 3.038 | 3.038 | 22.842 | 3.133 | 22.842 | 3.133 | 5.302 | 1.490 | 1.0212 | 0.2693 | 0.3701 |
| kp35_kd0.5 | sim | complete_support | support_leg | right | hip_roll | 3 | 0.320 | 3.038 | 3.038 | 18.737 | 8.288 | 15.604 | 3.064 | 5.351 | 0.526 | 0.9046 | 0.1028 | 0.3829 |
| kp35_kd0.5 | sim | complete_support | support_leg | right | knee_pitch | 3 | 0.320 | 3.038 | 3.038 | 13.181 | 3.133 | 12.201 | 0.000 | 4.608 | 1.439 | 1.0011 | 0.4205 | 0.3051 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.310 | 7.771 | 3.128 | 15.833 | 9.792 | 14.167 | 8.125 | 2.821 | 1.008 | 0.3098 | 0.1885 | 0.1049 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | left | ankle_roll | 2 | 0.310 | 3.128 | 4.741 | 28.854 | 12.917 | 27.187 | 8.229 | 2.263 | 0.382 | 0.5064 | 0.0688 | 0.2288 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | left | hip_pitch | 2 | 0.310 | 3.128 | 3.128 | 24.271 | 3.229 | 24.271 | 1.667 | 3.992 | 0.687 | 0.6129 | 0.1914 | 0.1580 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | left | hip_roll | 2 | 0.310 | 3.128 | 3.128 | 16.042 | 9.687 | 12.812 | 6.562 | 9.054 | 0.553 | 1.6710 | 0.0884 | 0.6107 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | left | knee_pitch | 2 | 0.310 | 3.128 | 3.128 | 16.146 | 6.458 | 14.583 | 4.792 | 3.126 | 1.655 | 0.6559 | 0.4519 | 0.2885 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.363 | 2.682 | 4.533 | 15.505 | 6.512 | 13.627 | 6.512 | 2.554 | 1.252 | 0.5293 | 0.2497 | 0.2556 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | right | ankle_roll | 3 | 0.363 | 2.682 | 2.682 | 30.209 | 15.479 | 30.209 | 8.218 | 2.295 | 0.375 | 0.3615 | 0.0660 | 0.0920 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | right | hip_pitch | 3 | 0.363 | 8.945 | 2.682 | 22.970 | 4.660 | 22.017 | 2.831 | 5.710 | 0.956 | 0.6924 | 0.2118 | 0.2220 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | right | hip_roll | 3 | 0.363 | 2.682 | 2.682 | 34.018 | 9.219 | 31.338 | 6.512 | 8.592 | 0.479 | 1.5714 | 0.1014 | 0.6404 |
| kp35_kd0.5 | sim | complete_swing | swing_leg | right | knee_pitch | 3 | 0.363 | 2.682 | 2.682 | 20.192 | 10.920 | 20.192 | 9.117 | 2.835 | 1.150 | 0.6090 | 0.3663 | 0.2393 |
| kp40_kd0.5 | sim | complete_support | support_leg | left | ankle_pitch | 3 | 0.360 | 2.707 | 3.585 | 14.071 | 11.130 | 10.387 | 10.229 | 4.364 | 1.137 | 0.7365 | 0.1369 | 0.3646 |
| kp40_kd0.5 | sim | complete_support | support_leg | left | ankle_roll | 3 | 0.360 | 2.707 | 2.707 | 28.647 | 12.932 | 25.944 | 8.268 | 1.449 | 1.291 | 0.4460 | 0.2775 | 0.1338 |
| kp40_kd0.5 | sim | complete_support | support_leg | left | hip_pitch | 3 | 0.360 | 2.707 | 2.707 | 33.469 | 2.782 | 33.469 | 1.882 | 3.473 | 1.006 | 0.6005 | 0.2650 | 0.1883 |
| kp40_kd0.5 | sim | complete_support | support_leg | left | hip_roll | 3 | 0.360 | 2.707 | 2.707 | 26.923 | 2.782 | 24.141 | 2.782 | 5.580 | 0.682 | 0.8494 | 0.1335 | 0.3605 |
| kp40_kd0.5 | sim | complete_support | support_leg | left | knee_pitch | 3 | 0.360 | 2.707 | 2.707 | 12.110 | 5.565 | 11.130 | 3.683 | 4.608 | 1.433 | 1.1085 | 0.4965 | 0.2503 |
| kp40_kd0.5 | sim | complete_support | support_leg | right | ankle_pitch | 3 | 0.337 | 3.841 | 2.888 | 17.015 | 11.006 | 14.041 | 11.006 | 3.419 | 0.709 | 0.7454 | 0.1387 | 0.3631 |
| kp40_kd0.5 | sim | complete_support | support_leg | right | ankle_roll | 3 | 0.337 | 2.888 | 2.888 | 23.671 | 13.890 | 20.786 | 7.881 | 1.835 | 0.633 | 0.3552 | 0.0946 | 0.1659 |
| kp40_kd0.5 | sim | complete_support | support_leg | right | hip_pitch | 3 | 0.337 | 2.888 | 2.888 | 30.722 | 2.974 | 29.770 | 2.974 | 5.020 | 1.404 | 1.0034 | 0.2747 | 0.3481 |
| kp40_kd0.5 | sim | complete_support | support_leg | right | hip_roll | 3 | 0.337 | 2.888 | 2.888 | 19.716 | 8.922 | 16.742 | 4.016 | 5.281 | 0.506 | 0.9011 | 0.1021 | 0.3936 |
| kp40_kd0.5 | sim | complete_support | support_leg | right | knee_pitch | 3 | 0.337 | 2.888 | 2.888 | 18.825 | 2.974 | 18.825 | 0.000 | 4.167 | 1.393 | 0.9471 | 0.4229 | 0.2956 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.335 | 4.419 | 2.904 | 16.650 | 11.962 | 13.659 | 10.534 | 2.189 | 1.040 | 0.2464 | 0.1971 | 0.1225 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | left | ankle_roll | 2 | 0.335 | 2.904 | 4.419 | 26.781 | 11.962 | 25.218 | 7.544 | 2.344 | 0.576 | 0.5103 | 0.1253 | 0.2028 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | left | hip_pitch | 2 | 0.335 | 2.904 | 2.904 | 25.218 | 2.991 | 25.218 | 0.000 | 3.656 | 0.645 | 0.5829 | 0.1875 | 0.1348 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | left | hip_roll | 2 | 0.335 | 2.904 | 2.904 | 16.246 | 8.972 | 13.256 | 5.981 | 8.157 | 0.547 | 1.6272 | 0.1011 | 0.5612 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | left | knee_pitch | 2 | 0.335 | 2.904 | 2.904 | 23.790 | 5.981 | 23.790 | 2.856 | 2.857 | 1.714 | 0.6990 | 0.5096 | 0.3045 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.360 | 2.707 | 2.707 | 23.003 | 4.585 | 23.003 | 4.585 | 3.165 | 1.274 | 0.5675 | 0.2848 | 0.2206 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | right | ankle_roll | 3 | 0.360 | 2.707 | 2.707 | 33.232 | 16.774 | 31.430 | 8.427 | 2.480 | 0.263 | 0.3497 | 0.0466 | 0.0911 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | right | hip_pitch | 3 | 0.360 | 10.828 | 2.707 | 25.200 | 2.782 | 25.200 | 1.881 | 6.400 | 0.874 | 0.7220 | 0.2006 | 0.2170 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | right | hip_roll | 3 | 0.360 | 2.707 | 2.707 | 34.370 | 8.347 | 31.667 | 5.565 | 9.154 | 0.467 | 1.6624 | 0.0984 | 0.6464 |
| kp40_kd0.5 | sim | complete_swing | swing_leg | right | knee_pitch | 3 | 0.360 | 2.707 | 2.707 | 22.260 | 8.268 | 21.358 | 7.367 | 2.584 | 1.168 | 0.5863 | 0.3772 | 0.2272 |
| kp40_kd0.8 | real | complete_support | support_leg | left | ankle_pitch | 3 | 0.313 | 3.541 | 3.541 | 12.749 | 7.094 | 9.055 | 4.527 | 3.345 | 1.268 | 0.4623 | 0.2228 | 0.3402 |
| kp40_kd0.8 | real | complete_support | support_leg | left | ankle_roll | 3 | 0.313 | 3.541 | 3.541 | 34.613 | 11.327 | 34.613 | 9.367 | 3.992 | 1.746 | 0.6672 | 0.2955 | 0.2079 |
| kp40_kd0.8 | real | complete_support | support_leg | left | hip_pitch | 3 | 0.313 | 3.541 | 3.541 | 41.884 | 2.567 | 41.884 | 1.666 | 12.365 | 1.097 | 1.1584 | 0.2263 | 0.4076 |
| kp40_kd0.8 | real | complete_support | support_leg | left | hip_roll | 3 | 0.313 | 3.541 | 3.541 | 18.304 | 7.995 | 15.670 | 2.499 | 11.087 | 0.375 | 1.4334 | 0.0848 | 0.6839 |
| kp40_kd0.8 | real | complete_support | support_leg | left | knee_pitch | 3 | 0.313 | 3.541 | 3.541 | 23.825 | 2.567 | 23.825 | 1.734 | 6.232 | 1.608 | 1.1619 | 0.3304 | 0.2478 |
| kp40_kd0.8 | real | complete_support | support_leg | right | ankle_pitch | 3 | 0.317 | 4.073 | 4.073 | 16.740 | 10.588 | 15.664 | 7.394 | 4.844 | 1.990 | 0.4638 | 0.2918 | 0.3335 |
| kp40_kd0.8 | real | complete_support | support_leg | right | ankle_roll | 3 | 0.317 | 3.063 | 3.063 | 34.659 | 14.856 | 34.659 | 12.705 | 6.147 | 3.769 | 0.6464 | 0.4892 | 0.2911 |
| kp40_kd0.8 | real | complete_support | support_leg | right | hip_pitch | 3 | 0.317 | 5.147 | 3.063 | 48.508 | 5.243 | 48.508 | 2.117 | 15.652 | 0.722 | 1.0776 | 0.1434 | 0.2619 |
| kp40_kd0.8 | real | complete_support | support_leg | right | hip_roll | 3 | 0.317 | 3.063 | 3.063 | 34.725 | 8.436 | 30.556 | 5.210 | 18.739 | 0.663 | 1.6795 | 0.1556 | 0.6922 |
| kp40_kd0.8 | real | complete_support | support_leg | right | knee_pitch | 3 | 0.317 | 4.073 | 3.063 | 43.163 | 3.160 | 43.163 | 3.160 | 4.585 | 1.720 | 0.4773 | 0.3459 | 0.1485 |
| kp40_kd0.8 | real | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.315 | 3.078 | 3.078 | 33.323 | 9.477 | 30.096 | 9.477 | 2.033 | 1.875 | 0.2744 | 0.3445 | 0.1228 |
| kp40_kd0.8 | real | complete_swing | swing_leg | left | ankle_roll | 2 | 0.315 | 3.078 | 4.594 | 34.885 | 11.091 | 34.885 | 11.091 | 1.652 | 3.198 | 0.2694 | 0.3454 | 0.1344 |
| kp40_kd0.8 | real | complete_swing | swing_leg | left | hip_pitch | 2 | 0.315 | 3.078 | 3.078 | 35.037 | 3.176 | 35.037 | 3.176 | 11.129 | 1.218 | 0.9048 | 0.2868 | 0.3047 |
| kp40_kd0.8 | real | complete_swing | swing_leg | left | hip_roll | 2 | 0.315 | 3.078 | 3.078 | 23.845 | 11.040 | 20.669 | 4.688 | 5.461 | 0.225 | 0.5150 | 0.0513 | 0.1603 |
| kp40_kd0.8 | real | complete_swing | swing_leg | left | knee_pitch | 2 | 0.315 | 3.078 | 3.078 | 36.499 | 3.176 | 36.499 | 3.176 | 6.512 | 4.136 | 1.3185 | 0.7279 | 0.4952 |
| kp40_kd0.8 | real | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.313 | 4.354 | 3.541 | 31.323 | 14.096 | 29.362 | 13.263 | 4.100 | 1.520 | 0.4730 | 0.2865 | 0.1248 |
| kp40_kd0.8 | real | complete_swing | swing_leg | right | ankle_roll | 3 | 0.313 | 5.393 | 6.044 | 31.238 | 12.817 | 30.405 | 12.817 | 2.844 | 4.970 | 0.4761 | 0.4880 | 0.1801 |
| kp40_kd0.8 | real | complete_swing | swing_leg | right | hip_pitch | 3 | 0.313 | 3.541 | 3.541 | 40.201 | 7.162 | 40.201 | 5.428 | 12.736 | 0.551 | 1.2735 | 0.0945 | 0.3263 |
| kp40_kd0.8 | real | complete_swing | swing_leg | right | hip_roll | 3 | 0.313 | 3.541 | 3.541 | 34.681 | 9.122 | 31.281 | 5.428 | 8.324 | 0.181 | 1.2356 | 0.0531 | 0.2755 |
| kp40_kd0.8 | real | complete_swing | swing_leg | right | knee_pitch | 3 | 0.313 | 3.541 | 3.541 | 32.273 | 1.734 | 32.273 | 1.734 | 5.367 | 3.836 | 0.8172 | 0.7294 | 0.4070 |
| kp50_kd0.8 | sim | complete_support | support_leg | left | ankle_pitch | 3 | 0.357 | 3.629 | 5.430 | 11.243 | 11.217 | 8.439 | 10.291 | 3.998 | 1.182 | 0.7074 | 0.1548 | 0.3312 |
| kp50_kd0.8 | sim | complete_support | support_leg | left | ankle_roll | 3 | 0.357 | 2.728 | 2.728 | 23.359 | 13.042 | 22.433 | 10.264 | 1.474 | 1.175 | 0.4416 | 0.2957 | 0.0976 |
| kp50_kd0.8 | sim | complete_support | support_leg | left | hip_pitch | 3 | 0.357 | 2.728 | 2.728 | 33.598 | 2.804 | 32.672 | 0.952 | 3.287 | 0.928 | 0.5666 | 0.2589 | 0.1903 |
| kp50_kd0.8 | sim | complete_support | support_leg | left | hip_roll | 3 | 0.357 | 2.728 | 2.728 | 19.577 | 4.656 | 15.846 | 4.656 | 5.015 | 0.736 | 0.8444 | 0.1514 | 0.3279 |
| kp50_kd0.8 | sim | complete_support | support_leg | left | knee_pitch | 3 | 0.357 | 2.728 | 2.728 | 10.212 | 5.608 | 10.212 | 3.730 | 4.446 | 1.419 | 1.0456 | 0.4847 | 0.2553 |
| kp50_kd0.8 | sim | complete_support | support_leg | right | ankle_pitch | 3 | 0.341 | 2.871 | 2.871 | 20.104 | 10.776 | 15.024 | 9.882 | 3.557 | 0.894 | 0.7491 | 0.1381 | 0.3888 |
| kp50_kd0.8 | sim | complete_support | support_leg | right | ankle_roll | 3 | 0.341 | 2.871 | 2.871 | 24.290 | 13.673 | 21.551 | 9.764 | 1.826 | 0.568 | 0.3112 | 0.0944 | 0.1258 |
| kp50_kd0.8 | sim | complete_support | support_leg | right | hip_pitch | 3 | 0.341 | 2.871 | 2.871 | 31.732 | 2.957 | 31.732 | 2.957 | 5.025 | 1.480 | 1.0222 | 0.3034 | 0.3550 |
| kp50_kd0.8 | sim | complete_support | support_leg | right | hip_roll | 3 | 0.341 | 2.871 | 2.871 | 22.208 | 6.966 | 19.251 | 2.004 | 5.226 | 0.431 | 0.8845 | 0.1010 | 0.3865 |
| kp50_kd0.8 | sim | complete_support | support_leg | right | knee_pitch | 3 | 0.341 | 2.871 | 2.871 | 13.079 | 2.957 | 12.186 | 0.000 | 4.552 | 1.414 | 0.9932 | 0.4349 | 0.3001 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | left | ankle_pitch | 2 | 0.325 | 7.393 | 3.002 | 22.858 | 10.715 | 18.096 | 10.715 | 3.171 | 1.065 | 0.2734 | 0.1911 | 0.0895 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | left | ankle_roll | 2 | 0.325 | 3.002 | 3.002 | 26.192 | 13.810 | 23.097 | 7.858 | 2.218 | 0.876 | 0.4772 | 0.2252 | 0.1989 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | left | hip_pitch | 2 | 0.325 | 3.002 | 3.002 | 24.763 | 3.095 | 24.763 | 0.000 | 4.082 | 0.726 | 0.6017 | 0.2130 | 0.1443 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | left | hip_roll | 2 | 0.325 | 3.002 | 3.002 | 18.334 | 9.286 | 15.239 | 6.191 | 8.692 | 0.538 | 1.5360 | 0.0970 | 0.6059 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | left | knee_pitch | 2 | 0.325 | 3.002 | 3.002 | 21.668 | 6.191 | 21.668 | 3.095 | 2.881 | 1.630 | 0.6242 | 0.4574 | 0.2880 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | right | ankle_pitch | 3 | 0.357 | 2.728 | 2.728 | 24.259 | 4.656 | 22.354 | 4.656 | 3.106 | 1.320 | 0.5443 | 0.2599 | 0.2245 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | right | ankle_roll | 3 | 0.357 | 4.529 | 2.728 | 27.116 | 17.777 | 26.190 | 10.264 | 2.019 | 0.417 | 0.3103 | 0.0739 | 0.0596 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | right | hip_pitch | 3 | 0.357 | 9.084 | 2.728 | 20.582 | 4.656 | 19.656 | 0.926 | 5.665 | 0.879 | 0.6731 | 0.2113 | 0.2108 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | right | hip_roll | 3 | 0.357 | 2.728 | 2.728 | 40.132 | 7.434 | 38.254 | 3.704 | 8.107 | 0.435 | 1.5757 | 0.0967 | 0.6241 |
| kp50_kd0.8 | sim | complete_swing | swing_leg | right | knee_pitch | 3 | 0.357 | 2.728 | 2.728 | 19.656 | 7.460 | 18.703 | 7.460 | 2.682 | 1.193 | 0.5576 | 0.3824 | 0.2303 |

## Per Step

| dataset | phase | role | step_index | joint | curves | duration | target dominant hz | joint dominant hz | target dir hz | joint dir hz | target extrema hz | joint extrema hz | target path rad/s | joint path rad/s | target range | joint range | err rms |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| real | complete_support | support_leg | 1 | ankle_pitch | 4 | 0.180 | 5.339 | 5.339 | 23.367 | 5.645 | 20.582 | 5.645 | 6.559 | 1.262 | 0.5782 | 0.1710 | 0.2580 |
| real | complete_support | support_leg | 1 | ankle_roll | 4 | 0.180 | 5.339 | 5.339 | 26.153 | 5.645 | 26.153 | 1.669 | 3.454 | 2.160 | 0.5178 | 0.2459 | 0.2164 |
| real | complete_support | support_leg | 1 | hip_pitch | 4 | 0.180 | 11.132 | 5.339 | 32.444 | 1.190 | 32.444 | 1.190 | 15.737 | 1.275 | 1.2073 | 0.2286 | 0.5190 |
| real | complete_support | support_leg | 1 | hip_roll | 4 | 0.180 | 5.339 | 5.339 | 20.038 | 8.503 | 17.533 | 4.049 | 6.543 | 0.242 | 0.7937 | 0.0371 | 0.2919 |
| real | complete_support | support_leg | 1 | knee_pitch | 4 | 0.180 | 5.339 | 5.339 | 24.523 | 0.000 | 24.523 | 0.000 | 5.488 | 2.121 | 0.6929 | 0.3885 | 0.1963 |
| real | complete_support | support_leg | 2 | ankle_pitch | 4 | 0.312 | 1.496 | 3.111 | 6.761 | 8.035 | 4.483 | 4.951 | 2.060 | 0.893 | 0.2718 | 0.2022 | 0.4239 |
| real | complete_support | support_leg | 2 | ankle_roll | 4 | 0.312 | 3.111 | 3.892 | 35.998 | 24.060 | 35.998 | 20.905 | 6.048 | 0.791 | 0.7107 | 0.1099 | 0.2315 |
| real | complete_support | support_leg | 2 | hip_pitch | 4 | 0.312 | 5.507 | 3.825 | 54.372 | 3.946 | 54.372 | 2.405 | 12.503 | 0.505 | 1.0015 | 0.0941 | 0.2143 |
| real | complete_support | support_leg | 2 | hip_roll | 4 | 0.312 | 3.111 | 3.111 | 34.513 | 9.562 | 32.915 | 4.865 | 13.166 | 0.343 | 1.5783 | 0.0799 | 0.7955 |
| real | complete_support | support_leg | 2 | knee_pitch | 4 | 0.312 | 3.111 | 3.111 | 41.416 | 4.682 | 40.681 | 2.348 | 3.629 | 1.192 | 0.4644 | 0.2594 | 0.1528 |
| real | complete_support | support_leg | 3 | ankle_pitch | 4 | 0.385 | 2.540 | 3.165 | 12.924 | 8.426 | 10.959 | 4.583 | 1.620 | 1.323 | 0.2653 | 0.3379 | 0.3825 |
| real | complete_support | support_leg | 3 | ankle_roll | 4 | 0.385 | 2.540 | 2.540 | 26.574 | 12.222 | 25.284 | 10.986 | 4.529 | 2.244 | 0.7345 | 0.4187 | 0.2887 |
| real | complete_support | support_leg | 3 | hip_pitch | 4 | 0.385 | 2.540 | 2.540 | 43.246 | 2.606 | 43.246 | 1.236 | 14.671 | 1.736 | 1.5175 | 0.4629 | 0.5716 |
| real | complete_support | support_leg | 3 | hip_roll | 4 | 0.385 | 2.540 | 2.540 | 28.689 | 10.352 | 24.071 | 5.700 | 14.187 | 0.682 | 1.6570 | 0.1619 | 0.6903 |
| real | complete_support | support_leg | 3 | knee_pitch | 4 | 0.385 | 2.540 | 2.540 | 36.452 | 3.889 | 36.452 | 1.912 | 6.875 | 1.706 | 1.2474 | 0.4561 | 0.3421 |
| real | complete_support | support_leg | 4 | ankle_pitch | 4 | 0.373 | 2.610 | 2.908 | 21.502 | 7.578 | 20.893 | 6.557 | 4.225 | 1.106 | 0.4525 | 0.2243 | 0.3348 |
| real | complete_support | support_leg | 4 | ankle_roll | 4 | 0.373 | 3.638 | 3.543 | 35.694 | 17.768 | 35.183 | 17.258 | 5.446 | 1.155 | 0.6220 | 0.1771 | 0.2602 |
| real | complete_support | support_leg | 4 | hip_pitch | 4 | 0.373 | 2.745 | 2.745 | 47.646 | 5.410 | 47.646 | 3.238 | 15.797 | 0.971 | 1.7455 | 0.3048 | 0.4898 |
| real | complete_support | support_leg | 4 | hip_roll | 4 | 0.373 | 4.138 | 2.745 | 28.340 | 7.410 | 25.929 | 6.290 | 14.623 | 0.519 | 1.5398 | 0.0982 | 0.5771 |
| real | complete_support | support_leg | 4 | knee_pitch | 4 | 0.373 | 3.503 | 2.745 | 38.810 | 2.827 | 37.690 | 2.217 | 4.728 | 1.642 | 0.7095 | 0.4288 | 0.2286 |
| real | complete_support | support_leg | 5 | ankle_pitch | 4 | 0.307 | 3.549 | 4.131 | 9.070 | 8.945 | 7.850 | 4.028 | 2.451 | 0.866 | 0.3761 | 0.1915 | 0.3824 |
| real | complete_support | support_leg | 5 | ankle_roll | 4 | 0.307 | 3.549 | 3.549 | 21.531 | 13.628 | 21.531 | 11.350 | 4.914 | 1.303 | 0.7223 | 0.2033 | 0.2528 |
| real | complete_support | support_leg | 5 | hip_pitch | 4 | 0.307 | 3.549 | 3.549 | 43.441 | 2.933 | 43.441 | 1.250 | 13.769 | 1.362 | 1.3374 | 0.3006 | 0.4498 |
| real | complete_support | support_leg | 5 | hip_roll | 4 | 0.307 | 3.549 | 3.549 | 22.191 | 11.026 | 17.303 | 4.852 | 11.297 | 0.519 | 1.5120 | 0.1135 | 0.7398 |
| real | complete_support | support_leg | 5 | knee_pitch | 4 | 0.307 | 3.549 | 3.549 | 27.623 | 4.425 | 27.623 | 2.609 | 6.546 | 1.439 | 1.0523 | 0.3025 | 0.2860 |
| real | complete_support | support_leg | 6 | ankle_pitch | 4 | 0.313 | 3.909 | 2.297 | 20.436 | 7.106 | 18.016 | 4.711 | 4.609 | 1.189 | 0.5088 | 0.1921 | 0.3648 |
| real | complete_support | support_leg | 6 | ankle_roll | 4 | 0.313 | 3.103 | 3.078 | 34.291 | 9.525 | 34.291 | 8.719 | 5.546 | 2.244 | 0.5492 | 0.2582 | 0.2618 |
| real | complete_support | support_leg | 6 | hip_pitch | 4 | 0.313 | 3.103 | 3.103 | 47.854 | 2.369 | 47.854 | 0.806 | 16.747 | 1.470 | 1.4470 | 0.3497 | 0.4337 |
| real | complete_support | support_leg | 6 | hip_roll | 4 | 0.313 | 3.860 | 3.103 | 27.753 | 7.964 | 23.846 | 4.737 | 15.488 | 0.858 | 1.6952 | 0.2269 | 0.7202 |
| real | complete_support | support_leg | 6 | knee_pitch | 4 | 0.313 | 3.103 | 3.103 | 39.836 | 2.369 | 38.275 | 1.588 | 4.824 | 1.798 | 0.5774 | 0.3751 | 0.2042 |
| real | complete_swing | swing_leg | 2 | ankle_pitch | 4 | 0.180 | 6.475 | 5.339 | 19.870 | 6.835 | 15.894 | 2.661 | 4.828 | 1.976 | 0.3586 | 0.3364 | 0.1593 |
| real | complete_swing | swing_leg | 2 | ankle_roll | 4 | 0.180 | 7.977 | 5.339 | 27.977 | 13.950 | 26.662 | 12.635 | 6.097 | 1.642 | 0.5102 | 0.1890 | 0.1226 |
| real | complete_swing | swing_leg | 2 | hip_pitch | 4 | 0.180 | 5.339 | 5.339 | 28.861 | 5.645 | 28.861 | 4.329 | 10.209 | 0.966 | 0.7203 | 0.1414 | 0.3003 |
| real | complete_swing | swing_leg | 2 | hip_roll | 4 | 0.180 | 5.339 | 5.339 | 35.937 | 8.305 | 33.078 | 6.835 | 12.117 | 0.245 | 1.4464 | 0.0323 | 0.4801 |
| real | complete_swing | swing_leg | 2 | knee_pitch | 4 | 0.180 | 5.339 | 5.339 | 34.428 | 0.000 | 34.428 | 0.000 | 5.056 | 4.424 | 0.4363 | 0.7956 | 0.4731 |
| real | complete_swing | swing_leg | 3 | ankle_pitch | 4 | 0.312 | 3.945 | 3.111 | 35.121 | 6.422 | 32.773 | 4.018 | 2.647 | 1.895 | 0.2803 | 0.3368 | 0.1375 |
| real | complete_swing | swing_leg | 3 | ankle_roll | 4 | 0.312 | 3.111 | 3.111 | 35.107 | 8.770 | 32.702 | 7.964 | 1.634 | 3.382 | 0.2549 | 0.4317 | 0.1869 |
| real | complete_swing | swing_leg | 3 | hip_pitch | 4 | 0.312 | 3.111 | 3.111 | 45.800 | 3.211 | 45.800 | 3.211 | 8.382 | 1.267 | 0.9010 | 0.2533 | 0.3158 |
| real | complete_swing | swing_leg | 3 | hip_roll | 4 | 0.312 | 3.111 | 3.111 | 30.525 | 5.630 | 28.121 | 2.475 | 5.813 | 0.243 | 0.6888 | 0.0678 | 0.2214 |
| real | complete_swing | swing_leg | 3 | knee_pitch | 4 | 0.312 | 3.111 | 3.111 | 28.842 | 4.017 | 28.842 | 3.211 | 6.085 | 3.384 | 1.0753 | 0.6599 | 0.4458 |
| real | complete_swing | swing_leg | 4 | ankle_pitch | 4 | 0.385 | 2.540 | 2.540 | 24.839 | 8.543 | 21.672 | 7.254 | 3.462 | 1.958 | 0.4388 | 0.4471 | 0.2105 |
| real | complete_swing | swing_leg | 4 | ankle_roll | 4 | 0.385 | 2.540 | 3.873 | 35.821 | 9.890 | 35.821 | 8.600 | 4.092 | 2.160 | 0.6892 | 0.3101 | 0.1485 |
| real | complete_swing | swing_leg | 4 | hip_pitch | 4 | 0.385 | 3.746 | 2.540 | 34.357 | 5.842 | 34.357 | 3.235 | 14.234 | 0.733 | 1.2634 | 0.1685 | 0.3455 |
| real | complete_swing | swing_leg | 4 | hip_roll | 4 | 0.385 | 2.540 | 2.540 | 29.492 | 9.147 | 25.696 | 3.870 | 8.416 | 0.275 | 1.2978 | 0.0592 | 0.3919 |
| real | complete_swing | swing_leg | 4 | knee_pitch | 4 | 0.385 | 2.540 | 2.540 | 27.420 | 3.201 | 27.420 | 3.201 | 7.130 | 3.848 | 1.2004 | 0.8465 | 0.5339 |
| real | complete_swing | swing_leg | 5 | ankle_pitch | 4 | 0.373 | 4.138 | 2.745 | 31.482 | 6.290 | 29.021 | 6.290 | 2.286 | 2.212 | 0.4002 | 0.5022 | 0.2089 |
| real | complete_swing | swing_leg | 5 | ankle_roll | 4 | 0.373 | 2.745 | 4.003 | 33.175 | 7.216 | 32.665 | 7.216 | 2.378 | 2.499 | 0.4421 | 0.3697 | 0.2008 |
| real | complete_swing | swing_leg | 5 | hip_pitch | 4 | 0.373 | 2.745 | 2.745 | 39.626 | 3.337 | 39.017 | 2.317 | 10.945 | 1.269 | 1.3072 | 0.4033 | 0.3720 |
| real | complete_swing | swing_leg | 5 | hip_roll | 4 | 0.373 | 3.638 | 2.745 | 31.780 | 8.995 | 28.443 | 4.484 | 8.096 | 0.334 | 1.0992 | 0.0828 | 0.3876 |
| real | complete_swing | swing_leg | 5 | knee_pitch | 4 | 0.373 | 2.745 | 2.745 | 32.132 | 3.946 | 32.132 | 3.946 | 5.964 | 4.029 | 1.0065 | 0.8119 | 0.4413 |
| real | complete_swing | swing_leg | 6 | ankle_pitch | 4 | 0.307 | 4.159 | 2.507 | 29.990 | 7.549 | 28.799 | 6.329 | 3.308 | 1.922 | 0.4157 | 0.4238 | 0.2279 |
| real | complete_swing | swing_leg | 6 | ankle_roll | 4 | 0.307 | 3.549 | 3.726 | 29.034 | 8.255 | 27.814 | 8.255 | 3.945 | 3.138 | 0.5754 | 0.3206 | 0.1814 |
| real | complete_swing | swing_leg | 6 | hip_pitch | 4 | 0.307 | 3.549 | 3.549 | 42.404 | 6.138 | 42.404 | 4.322 | 13.349 | 1.723 | 1.5981 | 0.3838 | 0.6004 |
| real | complete_swing | swing_leg | 6 | hip_roll | 4 | 0.307 | 3.549 | 3.549 | 34.781 | 9.909 | 31.223 | 2.441 | 8.579 | 0.296 | 1.4876 | 0.0573 | 0.3943 |
| real | complete_swing | swing_leg | 6 | knee_pitch | 4 | 0.307 | 3.549 | 3.549 | 26.704 | 2.308 | 25.616 | 2.308 | 5.987 | 4.540 | 0.9772 | 0.8802 | 0.5574 |
| sim | complete_support | support_leg | 1 | ankle_pitch | 4 | 0.493 | 3.723 | 3.973 | 15.199 | 8.778 | 12.069 | 8.063 | 3.545 | 0.904 | 0.6739 | 0.1771 | 0.2359 |
| sim | complete_support | support_leg | 1 | ankle_roll | 4 | 0.493 | 2.353 | 2.353 | 23.574 | 13.567 | 21.501 | 9.158 | 1.711 | 0.963 | 0.4882 | 0.2336 | 0.1582 |
| sim | complete_support | support_leg | 1 | hip_pitch | 4 | 0.493 | 2.353 | 2.353 | 34.635 | 4.046 | 34.635 | 1.550 | 3.597 | 0.774 | 0.5667 | 0.2536 | 0.1929 |
| sim | complete_support | support_leg | 1 | hip_roll | 4 | 0.493 | 2.353 | 2.353 | 24.349 | 5.707 | 19.709 | 4.177 | 5.384 | 0.536 | 0.9989 | 0.1262 | 0.3312 |
| sim | complete_support | support_leg | 1 | knee_pitch | 4 | 0.493 | 2.353 | 2.353 | 15.068 | 4.932 | 14.332 | 2.668 | 4.550 | 1.304 | 1.1382 | 0.4518 | 0.2660 |
| sim | complete_support | support_leg | 2 | ankle_pitch | 4 | 0.285 | 3.458 | 3.458 | 14.053 | 11.179 | 10.772 | 11.179 | 4.738 | 0.796 | 0.7551 | 0.1324 | 0.3648 |
| sim | complete_support | support_leg | 2 | ankle_roll | 4 | 0.285 | 3.458 | 3.458 | 18.400 | 12.846 | 17.567 | 6.866 | 2.129 | 0.464 | 0.3531 | 0.0768 | 0.1835 |
| sim | complete_support | support_leg | 2 | hip_pitch | 4 | 0.285 | 3.458 | 3.458 | 30.768 | 3.584 | 30.768 | 2.448 | 5.195 | 1.261 | 0.9283 | 0.2265 | 0.3319 |
| sim | complete_support | support_leg | 2 | hip_roll | 4 | 0.285 | 3.458 | 3.458 | 19.589 | 8.783 | 16.004 | 4.669 | 5.411 | 0.436 | 0.8821 | 0.0910 | 0.4078 |
| sim | complete_support | support_leg | 2 | knee_pitch | 4 | 0.285 | 3.458 | 3.458 | 8.627 | 3.584 | 8.627 | 0.000 | 4.946 | 1.340 | 1.0423 | 0.3655 | 0.3013 |
| sim | complete_support | support_leg | 3 | ankle_pitch | 4 | 0.380 | 2.584 | 2.584 | 14.860 | 10.042 | 11.639 | 8.672 | 3.827 | 1.054 | 0.7157 | 0.1637 | 0.3654 |
| sim | complete_support | support_leg | 3 | ankle_roll | 4 | 0.380 | 2.584 | 2.584 | 25.450 | 9.770 | 22.016 | 6.695 | 1.572 | 0.862 | 0.4223 | 0.1997 | 0.1505 |
| sim | complete_support | support_leg | 3 | hip_pitch | 4 | 0.380 | 2.584 | 2.584 | 30.547 | 3.221 | 30.547 | 1.851 | 3.905 | 1.059 | 0.7385 | 0.2635 | 0.2287 |
| sim | complete_support | support_leg | 3 | hip_roll | 4 | 0.380 | 2.584 | 2.584 | 22.702 | 4.357 | 20.049 | 3.789 | 5.692 | 0.783 | 1.1000 | 0.1648 | 0.4271 |
| sim | complete_support | support_leg | 3 | knee_pitch | 4 | 0.380 | 2.584 | 2.584 | 10.191 | 5.305 | 10.191 | 2.760 | 4.143 | 1.408 | 1.0570 | 0.4872 | 0.2621 |
| sim | complete_support | support_leg | 4 | ankle_pitch | 4 | 0.345 | 2.822 | 2.822 | 21.003 | 12.398 | 16.671 | 11.703 | 3.225 | 0.989 | 0.7453 | 0.1448 | 0.4747 |
| sim | complete_support | support_leg | 4 | ankle_roll | 4 | 0.345 | 2.822 | 2.822 | 27.372 | 14.520 | 23.840 | 9.493 | 1.777 | 0.674 | 0.3789 | 0.1071 | 0.1917 |
| sim | complete_support | support_leg | 4 | hip_pitch | 4 | 0.345 | 2.822 | 2.822 | 26.069 | 2.904 | 25.355 | 2.904 | 4.544 | 1.417 | 0.9143 | 0.2872 | 0.3329 |
| sim | complete_support | support_leg | 4 | hip_roll | 4 | 0.345 | 2.822 | 2.822 | 20.829 | 5.895 | 17.925 | 2.971 | 5.289 | 0.596 | 0.9061 | 0.1154 | 0.3759 |
| sim | complete_support | support_leg | 4 | knee_pitch | 4 | 0.345 | 2.822 | 2.822 | 15.948 | 3.598 | 15.948 | 0.694 | 4.370 | 1.413 | 0.9838 | 0.4561 | 0.2739 |
| sim | complete_support | support_leg | 5 | ankle_pitch | 4 | 0.357 | 2.732 | 4.066 | 17.739 | 10.457 | 13.472 | 7.789 | 3.824 | 1.077 | 0.7392 | 0.1388 | 0.4221 |
| sim | complete_support | support_leg | 5 | ankle_roll | 4 | 0.357 | 2.732 | 3.490 | 26.531 | 11.845 | 23.845 | 9.104 | 1.475 | 1.088 | 0.4383 | 0.2314 | 0.1670 |
| sim | complete_support | support_leg | 5 | hip_pitch | 4 | 0.357 | 2.732 | 2.732 | 36.866 | 2.809 | 35.391 | 1.457 | 3.780 | 1.149 | 0.7005 | 0.2595 | 0.2449 |
| sim | complete_support | support_leg | 5 | hip_roll | 4 | 0.357 | 2.732 | 2.732 | 22.818 | 4.372 | 20.009 | 4.372 | 5.160 | 0.744 | 0.9144 | 0.1426 | 0.3650 |
| sim | complete_support | support_leg | 5 | knee_pitch | 4 | 0.357 | 2.732 | 2.732 | 12.485 | 4.838 | 12.485 | 2.028 | 4.378 | 1.415 | 1.0467 | 0.4774 | 0.2486 |
| sim | complete_support | support_leg | 6 | ankle_pitch | 4 | 0.358 | 3.436 | 2.722 | 22.979 | 9.053 | 21.586 | 8.383 | 3.683 | 0.756 | 0.7265 | 0.1554 | 0.3367 |
| sim | complete_support | support_leg | 6 | ankle_roll | 4 | 0.358 | 2.722 | 2.722 | 25.173 | 12.599 | 22.440 | 11.193 | 1.656 | 0.663 | 0.3750 | 0.1092 | 0.1940 |
| sim | complete_support | support_leg | 6 | hip_pitch | 4 | 0.358 | 2.722 | 2.722 | 29.892 | 2.798 | 29.892 | 2.798 | 5.137 | 1.244 | 0.9425 | 0.2682 | 0.3119 |
| sim | complete_support | support_leg | 6 | hip_roll | 4 | 0.358 | 2.722 | 2.722 | 24.977 | 7.079 | 21.521 | 2.798 | 4.989 | 0.576 | 0.9334 | 0.1220 | 0.3973 |
| sim | complete_support | support_leg | 6 | knee_pitch | 4 | 0.358 | 2.722 | 2.722 | 18.273 | 3.456 | 16.868 | 0.658 | 4.119 | 1.392 | 0.9653 | 0.4522 | 0.2788 |
| sim | complete_swing | swing_leg | 2 | ankle_pitch | 3 | 0.350 | 2.779 | 4.631 | 18.951 | 6.615 | 17.998 | 6.615 | 2.145 | 1.056 | 0.3653 | 0.1707 | 0.1702 |
| sim | complete_swing | swing_leg | 2 | ankle_roll | 3 | 0.350 | 3.680 | 2.779 | 24.856 | 14.349 | 23.930 | 10.482 | 2.311 | 0.575 | 0.3492 | 0.1121 | 0.0625 |
| sim | complete_swing | swing_leg | 2 | hip_pitch | 3 | 0.350 | 10.191 | 2.779 | 25.810 | 6.615 | 23.932 | 3.811 | 5.074 | 0.712 | 0.6102 | 0.1999 | 0.2020 |
| sim | complete_swing | swing_leg | 2 | hip_roll | 3 | 0.350 | 2.779 | 2.779 | 38.088 | 10.454 | 38.088 | 6.670 | 8.482 | 0.410 | 1.5365 | 0.0875 | 0.5910 |
| sim | complete_swing | swing_leg | 2 | knee_pitch | 3 | 0.350 | 2.779 | 2.779 | 20.091 | 5.717 | 20.091 | 5.717 | 2.304 | 1.184 | 0.5188 | 0.3498 | 0.2339 |
| sim | complete_swing | swing_leg | 3 | ankle_pitch | 4 | 0.285 | 5.828 | 3.458 | 18.954 | 12.368 | 15.673 | 11.534 | 2.564 | 1.048 | 0.2263 | 0.1804 | 0.0942 |
| sim | complete_swing | swing_leg | 3 | ankle_roll | 4 | 0.285 | 3.458 | 5.022 | 22.160 | 10.928 | 19.712 | 9.314 | 2.318 | 0.593 | 0.4549 | 0.1207 | 0.1821 |
| sim | complete_swing | swing_leg | 3 | hip_pitch | 4 | 0.285 | 3.458 | 3.458 | 23.348 | 3.584 | 23.348 | 1.970 | 3.838 | 0.718 | 0.5757 | 0.1853 | 0.1526 |
| sim | complete_swing | swing_leg | 3 | hip_roll | 4 | 0.285 | 3.458 | 3.458 | 18.580 | 10.753 | 16.132 | 6.866 | 8.687 | 0.432 | 1.6428 | 0.0679 | 0.5839 |
| sim | complete_swing | swing_leg | 3 | knee_pitch | 4 | 0.285 | 3.458 | 3.458 | 18.878 | 6.032 | 18.878 | 2.803 | 2.940 | 1.587 | 0.6032 | 0.4057 | 0.2736 |
| sim | complete_swing | swing_leg | 4 | ankle_pitch | 4 | 0.380 | 3.139 | 2.584 | 21.390 | 6.314 | 18.131 | 5.746 | 3.291 | 1.307 | 0.5837 | 0.2748 | 0.2786 |
| sim | complete_swing | swing_leg | 4 | ankle_roll | 4 | 0.380 | 2.584 | 2.584 | 27.915 | 16.080 | 27.239 | 7.156 | 1.864 | 0.249 | 0.3474 | 0.0458 | 0.1250 |
| sim | complete_swing | swing_leg | 4 | hip_pitch | 4 | 0.380 | 7.973 | 2.584 | 26.000 | 2.653 | 25.432 | 1.938 | 5.811 | 1.004 | 0.7714 | 0.2198 | 0.2169 |
| sim | complete_swing | swing_leg | 4 | hip_roll | 4 | 0.380 | 2.584 | 2.584 | 31.155 | 6.529 | 27.827 | 5.139 | 8.357 | 0.515 | 1.5986 | 0.1231 | 0.6511 |
| sim | complete_swing | swing_leg | 4 | knee_pitch | 4 | 0.380 | 2.584 | 2.584 | 20.400 | 9.984 | 19.686 | 8.614 | 3.274 | 1.289 | 0.7723 | 0.3901 | 0.2476 |
| sim | complete_swing | swing_leg | 5 | ankle_pitch | 4 | 0.345 | 5.726 | 2.822 | 19.702 | 7.970 | 18.273 | 7.256 | 2.842 | 1.009 | 0.4142 | 0.1991 | 0.1767 |
| sim | complete_swing | swing_leg | 5 | ankle_roll | 4 | 0.345 | 2.822 | 4.849 | 31.190 | 13.025 | 29.782 | 4.332 | 2.529 | 0.509 | 0.4930 | 0.1106 | 0.1997 |
| sim | complete_swing | swing_leg | 5 | hip_pitch | 4 | 0.345 | 2.822 | 2.822 | 23.879 | 2.904 | 23.879 | 0.694 | 4.915 | 0.777 | 0.6606 | 0.1988 | 0.1717 |
| sim | complete_swing | swing_leg | 5 | hip_roll | 4 | 0.345 | 2.822 | 2.822 | 23.713 | 7.323 | 20.809 | 4.332 | 9.760 | 0.604 | 1.6226 | 0.1154 | 0.6100 |
| sim | complete_swing | swing_leg | 5 | knee_pitch | 4 | 0.345 | 2.822 | 2.822 | 22.277 | 6.502 | 21.496 | 5.094 | 3.183 | 1.544 | 0.6857 | 0.4642 | 0.2855 |
| sim | complete_swing | swing_leg | 6 | ankle_pitch | 4 | 0.357 | 2.732 | 2.732 | 24.540 | 4.943 | 24.540 | 4.161 | 3.354 | 1.239 | 0.5540 | 0.2808 | 0.1760 |
| sim | complete_swing | swing_leg | 6 | ankle_roll | 4 | 0.357 | 3.408 | 2.732 | 31.730 | 15.866 | 29.492 | 9.000 | 2.457 | 0.269 | 0.3994 | 0.0433 | 0.1176 |
| sim | complete_swing | swing_leg | 6 | hip_pitch | 4 | 0.357 | 7.340 | 2.732 | 19.630 | 2.809 | 19.630 | 0.000 | 6.058 | 0.882 | 0.7175 | 0.1938 | 0.2134 |
| sim | complete_swing | swing_leg | 6 | hip_roll | 4 | 0.357 | 2.732 | 2.732 | 33.175 | 8.428 | 29.707 | 4.180 | 9.001 | 0.520 | 1.6705 | 0.1011 | 0.6108 |
| sim | complete_swing | swing_leg | 6 | knee_pitch | 4 | 0.357 | 2.732 | 2.732 | 21.695 | 8.982 | 21.019 | 8.324 | 2.950 | 1.355 | 0.6389 | 0.4255 | 0.2570 |

## Skipped Phase Windows

Skipped rows: `9`. See `forward_x_failure_first6_complete_phase_skipped.csv` for details.
