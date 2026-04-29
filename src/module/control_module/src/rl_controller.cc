#include "control_module/rl_controller.h"
#include <string.h>
#include <iostream>
#include <limits>

namespace xyber_x1_infer::rl_control_module {

RLController::RLController(const bool use_sim_handles)
    : ControllerBase(use_sim_handles),
      memory_info_(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault)) {
}

void RLController::Init(const YAML::Node& cfg_node) {
  // 初始化 joint_names_
  joint_names_.clear();
  joint_names_ = cfg_node["joint_list"].as<std::vector<std::string>>();
  // printf("joint_names_: ");
  // for (const auto &name : joint_names_) {
  //   printf("%s ", name.c_str());
  // }
  // printf("\n");
  joint_state_data_.name = joint_names_;
  joint_state_data_.position.resize(joint_names_.size(), 0.0);
  joint_state_data_.velocity.resize(joint_names_.size(), 0.0);
  joint_state_data_.effort.resize(joint_names_.size(), 0.0);

  // 初始化 joint_conf_
  joint_conf_.init_state = Eigen::Map<vector_t>(cfg_node["init_state"].as<std::vector<double>>().data(), cfg_node["init_state"].as<std::vector<double>>().size());
  joint_conf_.stiffness = Eigen::Map<vector_t>(cfg_node["stiffness"].as<std::vector<double>>().data(), cfg_node["stiffness"].as<std::vector<double>>().size());
  joint_conf_.damping = Eigen::Map<vector_t>(cfg_node["damping"].as<std::vector<double>>().data(), cfg_node["damping"].as<std::vector<double>>().size());
  // std::cout << "init_state: " << joint_conf_.init_state.transpose() << std::endl;
  // std::cout << "stiffness: " << joint_conf_.stiffness.transpose() << std::endl;
  // std::cout << "damping: " << joint_conf_.damping.transpose() << std::endl;

  // ------
  // yumx:加载关节物理限位（按 joint_list 顺序）
  {
    const auto& limits_node = cfg_node["joint_limits"];
    const size_t n = joint_names_.size();
    joint_conf_.pos_limit_lower.resize(n);
    joint_conf_.pos_limit_upper.resize(n);
    for (size_t ii = 0; ii < n; ++ii) {
      const std::string& name = joint_names_[ii];
      if (limits_node[name]) {
        joint_conf_.pos_limit_lower(ii) = limits_node[name]["lower"].as<double>();
        joint_conf_.pos_limit_upper(ii) = limits_node[name]["upper"].as<double>();
      } else {
        // 若 YAML 中缺少该关节限位，使用无穷大（不限位）
        joint_conf_.pos_limit_lower(ii) = -std::numeric_limits<double>::infinity();
        joint_conf_.pos_limit_upper(ii) =  std::numeric_limits<double>::infinity();
        fprintf(stderr, "[RLController] WARNING: no joint_limits found for '%s', skipping clamp.\n", name.c_str());
      }
    }
  }
  //-----------------

  // 其他 RL 参数
  // clang-format off
  walk_step_conf_.action_scale  = cfg_node["walk_step_conf"]["action_scale"].as<double>();
  walk_step_conf_.decimation    = cfg_node["walk_step_conf"]["decimation"].as<int32_t>();
  walk_step_conf_.cycle_time    = cfg_node["walk_step_conf"]["cycle_time"].as<double>();
  walk_step_conf_.sw_mode       = cfg_node["walk_step_conf"]["sw_mode"].as<bool>();
  walk_step_conf_.cmd_threshold = cfg_node["walk_step_conf"]["cmd_threshold"].as<double>();
  obs_scales_.lin_vel           = cfg_node["obs_scales"]["lin_vel"].as<double>();
  obs_scales_.ang_vel           = cfg_node["obs_scales"]["ang_vel"].as<double>();
  obs_scales_.dof_pos           = cfg_node["obs_scales"]["dof_pos"].as<double>();
  obs_scales_.dof_vel           = cfg_node["obs_scales"]["dof_vel"].as<double>();
  obs_scales_.quat              = cfg_node["obs_scales"]["quat"].as<double>();
  onnx_conf_.policy_file        = cfg_node["onnx_conf"]["policy_file"].as<std::string>();
  onnx_conf_.actions_size       = cfg_node["onnx_conf"]["actions_size"].as<int32_t>();
  onnx_conf_.observations_size  = cfg_node["onnx_conf"]["observations_size"].as<int32_t>();
  onnx_conf_.num_hist           = cfg_node["onnx_conf"]["num_hist"].as<int32_t>();
  onnx_conf_.observations_clip  = cfg_node["onnx_conf"]["observations_clip"].as<double>();
  onnx_conf_.actions_clip       = cfg_node["onnx_conf"]["actions_clip"].as<double>();
  lpf_conf_.wc                  = cfg_node["lpf_conf"]["wc"].as<double>();
  lpf_conf_.ts                  = cfg_node["lpf_conf"]["ts"].as<double>();
  auto paralle_list = cfg_node["lpf_conf"]["paralle_list"].as<std::vector<std::string>>();
  lpf_conf_.paralle_list        = std::set<std::string>(paralle_list.begin(), paralle_list.end());
  LoadModel();
  // clang-format on

  propri_.joint_pos.resize(onnx_conf_.actions_size);
  propri_.joint_vel.resize(onnx_conf_.actions_size);
  loop_count_ = 0;
  actions_.resize(onnx_conf_.actions_size);
  observations_.resize(onnx_conf_.observations_size * onnx_conf_.num_hist);
  last_actions_.resize(onnx_conf_.actions_size);
  last_actions_.setZero();
  propri_history_buffer_.resize(onnx_conf_.observations_size * onnx_conf_.num_hist);
  low_pass_filters_.clear();
  for (size_t i = 0; i < onnx_conf_.actions_size; ++i) {
    low_pass_filters_.emplace_back(100, 0.001);
  }

  last_pos_des_raw_.assign(onnx_conf_.actions_size, std::numeric_limits<double>::quiet_NaN());
  last_pos_des_lpf_.assign(onnx_conf_.actions_size, std::numeric_limits<double>::quiet_NaN());
  last_tau_des_raw_.assign(onnx_conf_.actions_size, std::numeric_limits<double>::quiet_NaN());
  last_tau_des_lpf_.assign(onnx_conf_.actions_size, std::numeric_limits<double>::quiet_NaN());
  last_is_parallel_joint_.assign(onnx_conf_.actions_size, 0);

  round3_diag_log_dir_ = "test_logs/data_csv";
  round3_diag_log_prefix_ = "t27_tracking_lag_b1_diag";
  std::filesystem::create_directories(round3_diag_log_dir_);
  round3_diag_log_max_count_ = 40 * (1000 / walk_step_conf_.decimation);
  round3_diag_log_count_ = 0;
  round3_diag_logging_enabled_ = true;
  round3_diag_logging_triggered_ = false;
  round3_diag_pending_frame_ = false;
}

void RLController::RestartController() {
  is_first_frame_ = true;
  round3_diag_pending_frame_ = false;
}

void RLController::Update() {
  UpdateStateEstimation();
  // compute observation & actions
  if (loop_count_ % walk_step_conf_.decimation == 0) {
    ComputeObservation();
    ComputeActions();
    round3_diag_pending_frame_ = round3_diag_logging_enabled_;
  }

  loop_count_++;
}

my_ros2_proto::msg::JointCommand RLController::GetJointCmdData() {
  my_ros2_proto::msg::JointCommand joint_cmd;
  joint_cmd.name = joint_names_;
  joint_cmd.position.resize(joint_names_.size());
  joint_cmd.velocity.resize(joint_names_.size());
  joint_cmd.effort.resize(joint_names_.size());
  joint_cmd.damping.resize(joint_names_.size());
  joint_cmd.stiffness.resize(joint_names_.size());

  // get action
  for (int ii = 0; ii < onnx_conf_.actions_size; ii++) {
    scalar_t pos_des = actions_[ii] * walk_step_conf_.action_scale + joint_conf_.init_state(ii);
    double stiffness = joint_conf_.stiffness(ii);
    double damping = joint_conf_.damping(ii);
    last_pos_des_raw_[ii] = pos_des;
    last_pos_des_lpf_[ii] = std::numeric_limits<double>::quiet_NaN();
    last_tau_des_raw_[ii] = std::numeric_limits<double>::quiet_NaN();
    last_tau_des_lpf_[ii] = std::numeric_limits<double>::quiet_NaN();
    //  ------
    //  yumx关节物理限位 clamp（在低通滤波前，避免滤波器记忆超量值）
    pos_des = std::max(static_cast<scalar_t>(joint_conf_.pos_limit_lower(ii)),
                       std::min(static_cast<scalar_t>(joint_conf_.pos_limit_upper(ii)), pos_des));
    last_pos_des_raw_[ii] = pos_des;

    //  ---------
    if (lpf_conf_.paralle_list.find(joint_names_[ii]) == lpf_conf_.paralle_list.end()) {
      last_is_parallel_joint_[ii] = 0;
      low_pass_filters_[ii].input(pos_des);
      double pos_des_lp = low_pass_filters_[ii].output();
      last_pos_des_lpf_[ii] = pos_des_lp;
      joint_cmd.position[ii] = pos_des_lp;
      joint_cmd.velocity[ii] = 0.0;
      joint_cmd.effort[ii] = 0.0;
      joint_cmd.stiffness[ii] = stiffness;
      joint_cmd.damping[ii] = damping;
    } else {
      last_is_parallel_joint_[ii] = 1;
      double tau_des = stiffness * (pos_des - propri_.joint_pos[ii]) + damping * (0.0 - propri_.joint_vel[ii]);
      last_tau_des_raw_[ii] = tau_des;
      low_pass_filters_[ii].input(tau_des);
      double tau_des_lp = low_pass_filters_[ii].output();
      last_tau_des_lpf_[ii] = tau_des_lp;
      joint_cmd.position[ii] = 0.0;
      joint_cmd.velocity[ii] = 0.0;
      joint_cmd.effort[ii] = tau_des_lp;
      joint_cmd.stiffness[ii] = 0.0;
      joint_cmd.damping[ii] = 0.0;
    }
    last_actions_(ii, 0) = actions_[ii];
  }
  if (round3_diag_pending_frame_) {
    LogRound3DiagnosticData();
    round3_diag_pending_frame_ = false;
  }
  return joint_cmd;
}

void RLController::LoadModel() {
  // create env
  std::shared_ptr<Ort::Env> onnxEnvPrt(new Ort::Env(ORT_LOGGING_LEVEL_WARNING, "LeggedOnnxController"));
  Ort::SessionOptions sessionOptions;
  sessionOptions.SetInterOpNumThreads(1);
  session_ptr_ = std::make_unique<Ort::Session>(*onnxEnvPrt, onnx_conf_.policy_file.c_str(), sessionOptions);

  // get input and output info
  input_names_.clear();
  output_names_.clear();
  input_shapes_.clear();
  output_shapes_.clear();

  Ort::AllocatorWithDefaultOptions allocator;
  for (size_t ii = 0; ii < session_ptr_->GetInputCount(); ++ii) {
    char* tempstring = new char[strlen(session_ptr_->GetInputNameAllocated(ii, allocator).get()) + 1];
    strcpy(tempstring, session_ptr_->GetInputNameAllocated(ii, allocator).get());
    input_names_.push_back(tempstring);
    input_shapes_.push_back(session_ptr_->GetInputTypeInfo(ii).GetTensorTypeAndShapeInfo().GetShape());
  }

  for (size_t ii = 0; ii < session_ptr_->GetOutputCount(); ++ii) {
    char* tempstring = new char[strlen(session_ptr_->GetOutputNameAllocated(ii, allocator).get()) + 1];
    strcpy(tempstring, session_ptr_->GetOutputNameAllocated(ii, allocator).get());
    output_names_.push_back(tempstring);
    output_shapes_.push_back(session_ptr_->GetOutputTypeInfo(ii).GetTensorTypeAndShapeInfo().GetShape());
  }
}

void RLController::UpdateStateEstimation() {
  {
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);
    for (size_t ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      std::string joint_name = joint_names_[ii];
      propri_.joint_pos(ii) = joint_state_data_.position[ii];
      propri_.joint_vel(ii) = joint_state_data_.velocity[ii];
    }
  }

  {
    std::shared_lock<std::shared_mutex> lock(imu_mutex_);
    propri_.base_ang_vel(0) = imu_data_.angular_velocity.x;
    propri_.base_ang_vel(1) = imu_data_.angular_velocity.y;
    propri_.base_ang_vel(2) = imu_data_.angular_velocity.z;

    vector3_t gravity_vector(0, 0, -1);
    quaternion_t quat;
    quat.x() = imu_data_.orientation.x;
    quat.y() = imu_data_.orientation.y;
    quat.z() = imu_data_.orientation.z;
    quat.w() = imu_data_.orientation.w;
    matrix_t inverse_rot = GetRotationMatrixFromZyxEulerAngles(QuatToZyx(quat)).inverse();
    propri_.projected_gravity = inverse_rot * gravity_vector;
    propri_.base_euler_xyz = QuatToXyz(quat);
  }
}

void RLController::ComputeObservation() {
  // actions
  vector_t propri_obs(onnx_conf_.observations_size);
  {
    std::shared_lock<std::shared_mutex> lock(joy_mutex_);
    double phase = duration<double>(high_resolution_clock::now().time_since_epoch()).count();
    if (walk_step_conf_.sw_mode) {
      double cmd_norm = std::sqrt(Square(joy_data_.linear.x) + Square(joy_data_.linear.y) + Square(joy_data_.angular.z));
      if (cmd_norm <= walk_step_conf_.cmd_threshold) {
        phase = 0;
      }
    }
    phase = phase / walk_step_conf_.cycle_time;
    last_phase_sin_ = sin(2 * M_PI * phase);
    last_phase_cos_ = cos(2 * M_PI * phase);
    last_cmd_linear_x_ = joy_data_.linear.x;
    last_cmd_linear_y_ = joy_data_.linear.y;
    last_cmd_angular_z_ = joy_data_.angular.z;

    // clang-format off
    propri_obs << last_phase_sin_,  // 1
                  last_phase_cos_,  // 1
                  joy_data_.linear.x * obs_scales_.lin_vel, // 1
                  joy_data_.linear.y * obs_scales_.lin_vel, // 1
                  joy_data_.angular.z, // 1
                  (propri_.joint_pos - joint_conf_.init_state) * obs_scales_.dof_pos, // action_size
                  propri_.joint_vel * obs_scales_.dof_vel, // action_size
                  last_actions_, // action_size
                  propri_.base_ang_vel * obs_scales_.ang_vel, // 3
                  propri_.base_euler_xyz * obs_scales_.quat; // 3
    // clang-format on
  }

  if (is_first_frame_) {
    for (size_t ii = 0; ii < joint_names_.size(); ++ii) {
      if (lpf_conf_.paralle_list.find(joint_names_[ii]) == lpf_conf_.paralle_list.end()) {
        // serial
        low_pass_filters_[ii].init(propri_.joint_pos[ii]);
      } else {
        // parallel
        low_pass_filters_[ii].init(0);
      }
    }

    // Set last_actions_ to 0
    for (int ii = 5 + onnx_conf_.actions_size * 2; ii < 5 + onnx_conf_.actions_size * 3; ++ii) {
      propri_obs(ii, 0) = 0.0;
    }
  
    for (int ii = 0; ii < onnx_conf_.num_hist; ++ii) {
      propri_history_buffer_.segment(ii * onnx_conf_.observations_size, onnx_conf_.observations_size) = propri_obs.cast<float>();
    }
    is_first_frame_ = false;
  }

  propri_history_buffer_.head(propri_history_buffer_.size() - onnx_conf_.observations_size) = propri_history_buffer_.tail(propri_history_buffer_.size() - onnx_conf_.observations_size);
  propri_history_buffer_.tail(onnx_conf_.observations_size) = propri_obs.cast<float>();

  for (int ii = 0; ii < (onnx_conf_.observations_size * onnx_conf_.num_hist); ++ii) {
    observations_[ii] = static_cast<float>(propri_history_buffer_[ii]);
  }
  // limit observations range
  scalar_t obs_min = -onnx_conf_.observations_clip;
  scalar_t obs_max = onnx_conf_.observations_clip;
  std::transform(observations_.begin(), observations_.end(), observations_.begin(),
                 [obs_min, obs_max](scalar_t x) { 
                   return std::max(obs_min, std::min(obs_max, x));
                 });
}

void RLController::ComputeActions() {
  // create input tensor object
  std::vector<Ort::Value> input_tensor;
  input_tensor.push_back(Ort::Value::CreateTensor<float>(memory_info_, observations_.data(), observations_.size(), input_shapes_[0].data(),input_shapes_[0].size()));

  std::vector<Ort::Value> output_values = session_ptr_->Run(Ort::RunOptions{}, input_names_.data(), input_tensor.data(), 1, output_names_.data(), 1);

  for (int i = 0; i < onnx_conf_.actions_size; ++i) {
    actions_[i] = *(output_values[0].GetTensorMutableData<float>() + i);
  }
  // limit action range
  scalar_t action_min = -onnx_conf_.actions_clip;
  scalar_t action_max = onnx_conf_.actions_clip;
  std::transform(actions_.begin(), actions_.end(), actions_.begin(),
                 [action_min, action_max](scalar_t x) {
                   return std::max(action_min, std::min(action_max, x));
                 });
}

bool RLController::DetectFootContact(int foot_idx) {
  int ankle_idx = (foot_idx == 0) ? 4 : 10;
  if (ankle_idx >= onnx_conf_.actions_size) {
    return false;
  }
  double vel_threshold = 0.5;
  return std::abs(propri_.joint_vel(ankle_idx)) < vel_threshold;
}

void RLController::LogRound3DiagnosticData() {
  bool walk_entered = walk_leg_entered_.load(std::memory_order_acquire);

  if (walk_entered && !round3_diag_logging_triggered_) {
    if (round3_diag_file_.is_open()) {
      round3_diag_file_.flush();
      round3_diag_file_.close();
    }

    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);
    std::tm tm_now{};
#ifdef _WIN32
    localtime_s(&tm_now, &time_t_now);
#else
    localtime_r(&time_t_now, &tm_now);
#endif
    char time_buf[64];
    std::strftime(time_buf, sizeof(time_buf), "%Y%m%d_%H%M%S", &tm_now);

    std::string diag_path =
        round3_diag_log_dir_ + "/" + round3_diag_log_prefix_ + "_" + std::string(time_buf) + ".csv";
    round3_diag_file_.open(diag_path);
    if (round3_diag_file_.is_open()) {
      round3_diag_file_
          << "timestamp_ns,phase_sin,phase_cos,cmd_linear_x,cmd_linear_y,cmd_angular_z,"
          << "left_contact,right_contact,base_euler_x,base_euler_y,base_euler_z,"
          << "base_ang_vel_x,base_ang_vel_y,base_ang_vel_z";
      for (const auto& name : joint_names_) {
        round3_diag_file_
            << ",action_" << name
            << ",pos_" << name
            << ",vel_" << name
            << ",effort_" << name
            << ",pos_des_raw_" << name
            << ",pos_des_lpf_" << name
            << ",tau_des_raw_" << name
            << ",tau_des_lpf_" << name
            << ",is_parallel_" << name;
      }
      if (!actuator_names_.empty()) {
        for (const auto& name : actuator_names_) {
          round3_diag_file_
              << ",actuator_cmd_pos_" << name
              << ",actuator_cmd_vel_" << name
              << ",actuator_cmd_effort_" << name
              << ",actuator_cmd_kp_" << name
              << ",actuator_cmd_kd_" << name
              << ",actuator_state_pos_" << name
              << ",actuator_state_vel_" << name
              << ",actuator_state_effort_" << name;
        }
      }
      round3_diag_file_ << "\n";
      round3_diag_logging_triggered_ = true;
      round3_diag_log_count_ = 0;
    }
  }

  if (!round3_diag_logging_triggered_ || round3_diag_log_count_ >= round3_diag_log_max_count_) {
    return;
  }

  auto now_ns = duration_cast<nanoseconds>(high_resolution_clock::now().time_since_epoch()).count();
  bool left_contact = DetectFootContact(0);
  bool right_contact = DetectFootContact(1);

  round3_diag_file_
      << now_ns
      << "," << last_phase_sin_
      << "," << last_phase_cos_
      << "," << last_cmd_linear_x_
      << "," << last_cmd_linear_y_
      << "," << last_cmd_angular_z_
      << "," << left_contact
      << "," << right_contact
      << "," << propri_.base_euler_xyz(0)
      << "," << propri_.base_euler_xyz(1)
      << "," << propri_.base_euler_xyz(2)
      << "," << propri_.base_ang_vel(0)
      << "," << propri_.base_ang_vel(1)
      << "," << propri_.base_ang_vel(2);

  {
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);
    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      round3_diag_file_
          << "," << actions_[ii]
          << "," << propri_.joint_pos(ii)
          << "," << propri_.joint_vel(ii)
          << "," << joint_state_data_.effort[ii]
          << "," << last_pos_des_raw_[ii]
          << "," << last_pos_des_lpf_[ii]
          << "," << last_tau_des_raw_[ii]
          << "," << last_tau_des_lpf_[ii]
          << "," << last_is_parallel_joint_[ii];
    }
  }
  {
    std::shared_lock<std::shared_mutex> lock(actuator_state_mutex_);
    if (!actuator_names_.empty()) {
      for (size_t ii = 0; ii < actuator_names_.size(); ++ii) {
        const bool cmd_valid = ii < actuator_cmd_data_.name.size();
        const bool state_valid = ii < actuator_state_data_.name.size();
        round3_diag_file_
            << ","
            << (cmd_valid ? actuator_cmd_data_.position[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (cmd_valid ? actuator_cmd_data_.velocity[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (cmd_valid ? actuator_cmd_data_.effort[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (cmd_valid ? actuator_cmd_data_.stiffness[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (cmd_valid ? actuator_cmd_data_.damping[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (state_valid ? actuator_state_data_.position[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (state_valid ? actuator_state_data_.velocity[ii] : std::numeric_limits<double>::quiet_NaN())
            << ","
            << (state_valid ? actuator_state_data_.effort[ii] : std::numeric_limits<double>::quiet_NaN());
      }
    }
  }
  round3_diag_file_ << "\n";

  round3_diag_log_count_++;
  if (round3_diag_log_count_ >= round3_diag_log_max_count_) {
    round3_diag_file_.flush();
    round3_diag_file_.close();
    round3_diag_logging_triggered_ = false;
  }
}

}  // namespace xyber_x1_infer::rl_control_module
