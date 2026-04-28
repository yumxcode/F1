#pragma once
#include <onnxruntime/onnxruntime_cxx_api.h>
#include <memory>
#include <set>
#include <atomic>
#include <fstream>
#include <filesystem>

#include "control_module/controller_base.h"
#include "control_module/rotation_tools.h"

namespace xyber_x1_infer::rl_control_module {

class RLController : public ControllerBase {
 public:
  RLController(const bool use_sim_handles);
  ~RLController() = default;

  void Init(const YAML::Node &cfg_node) override;
  void RestartController() override;

  void Update() override;
  my_ros2_proto::msg::JointCommand GetJointCmdData() override;

 private:
  void LoadModel();
  void UpdateStateEstimation();
  void ComputeObservation();
  void ComputeActions();

 private:
  struct WalkStepConf {
    double action_scale;
    int decimation;
    double cycle_time;
    bool sw_mode;
    double cmd_threshold;
  } walk_step_conf_;

  struct ObsScales {
    double lin_vel;
    double ang_vel;
    double dof_pos;
    double dof_vel;
    double quat;
  } obs_scales_;

  struct OnnxConf {
    std::string policy_file;
    int actions_size;
    int observations_size;
    int num_hist;
    double observations_clip;
    double actions_clip;
  } onnx_conf_;

  struct LPFConf {
    double wc;
    double ts;
    std::set<std::string> paralle_list;
  } lpf_conf_;

  // onnx
  std::unique_ptr<Ort::Session> session_ptr_;
  Ort::MemoryInfo memory_info_;
  std::vector<const char *> input_names_;
  std::vector<const char *> output_names_;
  std::vector<std::vector<int64_t>> input_shapes_;
  std::vector<std::vector<int64_t>> output_shapes_;

  // compute in algorithm
  std::vector<float> actions_;
  std::vector<float> observations_;
  vector_t last_actions_;
  // vector_t propri_history_buffer_;
  Eigen::Matrix<float, Eigen::Dynamic, 1> propri_history_buffer_;
  struct Proprioception {
    vector_t joint_pos;
    vector_t joint_vel;
    vector3_t base_ang_vel;
    vector3_t base_euler_xyz;
    vector3_t projected_gravity;
  } propri_;

  // other
  int64_t loop_count_;
  std::vector<digital_lp_filter<double>> low_pass_filters_;
  std::atomic_bool is_first_frame_{true};

  // T1 静态测试 CSV 日志（从 obs pipeline 中提取数据，与仿真对比）
  std::ofstream t1_joint_pos_file_;   // T1-1: (joint_pos - init_state) * dof_pos_scale
  std::ofstream t1_joint_vel_file_;   // T1-2: joint_vel * dof_vel_scale
  std::ofstream t1_imu_file_;         // T1-3: ang_vel * ang_vel_scale + euler * quat_scale
  bool t1_logging_enabled_{false};
  bool t1_logging_triggered_{false};  // 是否已触发记录
  std::atomic_bool zero_mode_entered_{false};  // zero 模式进入标志（由 ControlModule 设置）
  int t1_log_count_{0};
  int t1_log_max_count_{0};
  std::string t1_log_dir_;
  
 public:
  void SetZeroModeEntered(bool entered) { zero_mode_entered_.store(entered, std::memory_order_release); }
  void SetWalkLegEntered(bool entered) { walk_leg_entered_.store(entered, std::memory_order_release); }
  void SetT4RecordRequested(bool requested, const std::string& state_name = "") {
    if (requested && t4_trigger_state_ != state_name) {
      t4_logging_triggered_.store(false, std::memory_order_release);
    }
    t4_trigger_state_ = state_name;
    t4_record_requested_.store(requested, std::memory_order_release);
  }
  void UpdateT1Logging();  // 独立的 T1 日志更新，可在非活跃状态下调用
  void UpdateT4Logging();  // 独立的 T4 原始传感器日志更新，可在非活跃状态下调用（zero/stand/walk_leg 触发）
  
 private:

  // T2 测试 CSV 日志（进入 walk_leg 后触发记录）
  std::ofstream t2_gait_file_;       // T2-2 步态周期
  std::ofstream t2_joint_file_;      // T2-3 关节轨迹
  std::ofstream t2_pose_file_;       // T2-4 机身姿态
  std::ofstream t2_action_file_;     // T2-5 网络输出
  bool t2_logging_enabled_{false};
  bool t2_logging_triggered_{false};  // 是否已触发记录
  std::atomic_bool walk_leg_entered_{false};  // walk_leg 模式进入标志（由 ControlModule 设置）
  int t2_log_count_{0};
  int t2_log_max_count_{0};
  std::string t2_log_dir_;
  // T2 步态检测辅助变量
  bool last_contact_state_[2]{false, false};
  double last_contact_time_[2]{0.0, 0.0};

  void LogT2Data();
  bool DetectFootContact(int foot_idx);

  // T3 测试 CSV 日志（进入 walk_leg 后触发记录）
  std::ofstream t3_current_file_;       // T3 电机电流
  bool t3_logging_enabled_{false};
  bool t3_logging_triggered_{false};  // 是否已触发记录
  int t3_log_count_{0};
  int t3_log_max_count_{0};
  std::string t3_log_dir_;

  void LogT3Data();

  // T4 原始传感器数据记录（zero/stand/walk_leg 模式触发，记录未缩放的原始数据，40s @ 1000Hz）
  std::ofstream t4_raw_joint_pos_file_;   // T4-1: 原始关节位置 (rad)
  std::ofstream t4_raw_joint_vel_file_;   // T4-2: 原始关节速度 (rad/s)
  std::ofstream t4_raw_motor_current_file_; // T4-3: 原始电机电流 (A/Nm)
  std::ofstream t4_raw_imu_quat_file_;    // T4-4: 原始IMU四元数 (w,x,y,z)
  std::ofstream t4_raw_imu_gyro_file_;    // T4-5: 原始IMU角速度 (rad/s)
  std::ofstream t4_raw_imu_accel_file_;   // T4-6: 原始IMU加速度 (m/s^2)
  bool t4_logging_enabled_{false};
  std::atomic_bool t4_logging_triggered_{false};
  std::atomic_bool t4_record_requested_{false};  // T4 记录请求标志（由 ControlModule 在 zero/stand/walk_leg 时设置）
  std::string t4_trigger_state_;  // 触发 T4 记录时的状态名
  int t4_log_count_{0};
  int t4_log_max_count_{0};
  std::string t4_log_dir_;

  void LogT4RawSensorData();

  // T_M (Step 1) 网络输入观测向量记录 (binary float32, walk_leg 触发, 20s)
  FILE* tm_obs_bin_file_{nullptr};
  bool tm_logging_enabled_{false};
  bool tm_logging_triggered_{false};
  int tm_log_count_{0};
  int tm_log_max_count_{0};
  std::string tm_log_dir_;

  void LogTmData();

  // T_M 同步原始传感器记录（walk_leg 触发，20s @ 1000Hz，CSV，与 t26 obs 时间窗口对齐，用于 Step 3）
  std::ofstream tm_raw_joint_pos_file_;
  std::ofstream tm_raw_joint_vel_file_;
  std::ofstream tm_raw_motor_current_file_;
  std::ofstream tm_raw_imu_quat_file_;
  std::ofstream tm_raw_imu_gyro_file_;
  std::ofstream tm_raw_imu_accel_file_;
  bool tm_raw_logging_enabled_{false};
  bool tm_raw_logging_triggered_{false};
  int  tm_raw_log_count_{0};
  int  tm_raw_log_max_count_{0};

  void LogTmRawSensorData();

  // T_M25: ONNX action 输出记录 (CSV, walk_leg 触发, 20s @ 策略频率, 保存至 t_m/)
  std::ofstream tm25_action_file_;
  bool tm25_logging_enabled_{false};
  bool tm25_logging_triggered_{false};
  int  tm25_log_count_{0};
  int  tm25_log_max_count_{0};

  void LogTm25Data();
};

}  // namespace xyber_x1_infer::rl_control_module
