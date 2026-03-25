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

  // T1 静态测试 CSV 日志
  std::ofstream t1_log_file_;
  bool t1_logging_enabled_{false};
  bool t1_logging_triggered_{false};  // 是否已触发记录
  std::atomic_bool zero_mode_entered_{false};  // zero 模式进入标志（由 ControlModule 设置）
  int t1_log_count_{0};
  int t1_log_max_count_{0};
  std::string t1_log_dir_;
  
 public:
  void SetZeroModeEntered(bool entered) { zero_mode_entered_.store(entered, std::memory_order_release); }
  
 private:

  // T2 测试 CSV 日志
  std::ofstream t2_gait_file_;       // T2-2 步态周期
  std::ofstream t2_joint_file_;      // T2-3 关节轨迹
  std::ofstream t2_pose_file_;       // T2-4 机身姿态
  std::ofstream t2_action_file_;     // T2-5 网络输出
  bool t2_logging_enabled_{false};
  int t2_log_count_{0};
  int t2_log_max_count_{0};
  std::string t2_log_dir_;
  // T2 步态检测辅助变量
  bool last_contact_state_[2]{false, false};
  double last_contact_time_[2]{0.0, 0.0};

  void LogT2Data();
  bool DetectFootContact(int foot_idx);

  // T3 测试 CSV 日志
  std::ofstream t3_current_file_;       // T3 电机电流
  bool t3_logging_enabled_{false};
  int t3_log_count_{0};
  int t3_log_max_count_{0};
  std::string t3_log_dir_;

  void LogT3Data();
};

}  // namespace xyber_x1_infer::rl_control_module
