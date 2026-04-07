#include "control_module/rl_controller.h"
#include <string.h>
#include <iostream>

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

  // ---- T1 静态测试 CSV 日志初始化（从 obs pipeline 提取，与仿真对比） ----
  {
    t1_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t1_log_dir_);

    // T1 触发式记录，不在初始化时打开文件
    t1_log_max_count_ = 40000;  // 40s * 1000Hz
    t1_log_count_ = 0;
    t1_logging_enabled_ = true;
    t1_logging_triggered_ = false;

    fprintf(stderr, "[RLController] T1 logging enabled (3 CSV files, joints=%d, max 40s @ 1000Hz)\n",
            onnx_conf_.actions_size);
    fprintf(stderr, "  - T1-1: joint_pos obs (dof_pos_scale=%.4f)\n", obs_scales_.dof_pos);
    fprintf(stderr, "  - T1-2: joint_vel obs (dof_vel_scale=%.4f)\n", obs_scales_.dof_vel);
    fprintf(stderr, "  - T1-3: IMU obs (ang_vel_scale=%.4f, quat_scale=%.4f)\n", obs_scales_.ang_vel, obs_scales_.quat);
  }
  // ---- T1 日志初始化结束 ----

  // ---- T2 测试 CSV 日志初始化（触发式，进入 walk_leg 后开始记录） ----
  {
    t2_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t2_log_dir_);

    // 40s * (1000Hz / decimation) 帧
    t2_log_max_count_ = 40 * (1000 / walk_step_conf_.decimation);
    t2_log_count_ = 0;
    t2_logging_enabled_ = true;  // 启用功能，但等待触发
    t2_logging_triggered_ = false;

    // 初始化步态检测辅助变量
    last_contact_state_[0] = false;
    last_contact_state_[1] = false;
    last_contact_time_[0] = 0.0;
    last_contact_time_[1] = 0.0;

    fprintf(stderr, "[RLController] T2 logging enabled (max %d frames, waiting for walk_leg trigger)\n", t2_log_max_count_);
  }
  // ---- T2 日志初始化结束 ----

  // ---- T3 测试 CSV 日志初始化（触发式，进入 walk_leg 后开始记录） ----
  {
    t3_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t3_log_dir_);

    // 40s * (1000Hz / decimation) 帧
    t3_log_max_count_ = 40 * (1000 / walk_step_conf_.decimation);
    t3_log_count_ = 0;
    t3_logging_enabled_ = true;  // 启用功能，但等待触发
    t3_logging_triggered_ = false;

    fprintf(stderr, "[RLController] T3 logging enabled (max %d frames, waiting for walk_leg trigger)\n", t3_log_max_count_);
  }
  // ---- T3 日志初始化结束 ----

  // ---- T4 原始传感器数据 CSV 日志初始化（触发式，进入 walk_leg 后开始记录） ----
  {
    t4_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t4_log_dir_);

    // 40s * 1000Hz（原始传感器频率，不受 decimation 影响）
    t4_log_max_count_ = 40 * 1000;
    t4_log_count_ = 0;
    t4_logging_enabled_ = true;  // 启用功能，但等待触发
    t4_logging_triggered_ = false;

    fprintf(stderr, "[RLController] T4 raw sensor logging enabled (6 CSV files, max %d frames @ 1000Hz, waiting for walk_leg trigger)\n", t4_log_max_count_);
  }
  // ---- T4 日志初始化结束 ----

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
}

void RLController::RestartController() {
  is_first_frame_ = true;
}

void RLController::Update() {
  UpdateStateEstimation();
  // compute observation & actions
  if (loop_count_ % walk_step_conf_.decimation == 0) {
    ComputeObservation();
    ComputeActions();

    // T2 数据采集（仅在 decimation 周期记录，与策略同频）
    if (t2_logging_enabled_) {
      LogT2Data();
    }

    // T3 数据采集（仅在 decimation 周期记录，与策略同频）
    if (t3_logging_enabled_) {
      LogT3Data();
    }
  }

  // T4 原始传感器数据记录（每个 MainLoop 周期记录，1000Hz 全频率采样）
  if (t4_logging_enabled_) {
    LogT4RawSensorData();
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

    //  ------
    //  yumx关节物理限位 clamp（在低通滤波前，避免滤波器记忆超量值）
    pos_des = std::max(static_cast<scalar_t>(joint_conf_.pos_limit_lower(ii)),
                       std::min(static_cast<scalar_t>(joint_conf_.pos_limit_upper(ii)), pos_des));

    //  ---------
    if (lpf_conf_.paralle_list.find(joint_names_[ii]) == lpf_conf_.paralle_list.end()) {
      low_pass_filters_[ii].input(pos_des);
      double pos_des_lp = low_pass_filters_[ii].output();
      joint_cmd.position[ii] = pos_des_lp;
      joint_cmd.velocity[ii] = 0.0;
      joint_cmd.effort[ii] = 0.0;
      joint_cmd.stiffness[ii] = stiffness;
      joint_cmd.damping[ii] = damping;
    } else {
      double tau_des = stiffness * (pos_des - propri_.joint_pos[ii]) + damping * (0.0 - propri_.joint_vel[ii]);
      low_pass_filters_[ii].input(tau_des);
      double tau_des_lp = low_pass_filters_[ii].output();
      joint_cmd.position[ii] = 0.0;
      joint_cmd.velocity[ii] = 0.0;
      joint_cmd.effort[ii] = tau_des_lp;
      joint_cmd.stiffness[ii] = 0.0;
      joint_cmd.damping[ii] = 0.0;
    }
    last_actions_(ii, 0) = actions_[ii];
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

    // clang-format off
    propri_obs << sin(2 * M_PI * phase),  // 1
                  cos(2 * M_PI * phase),  // 1
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

void RLController::UpdateT1Logging() {
  if (!t1_logging_enabled_) {
    return;
  }

  // ---- 1. 读取最新传感器数据（与 obs pipeline 一致的方式） ----
  vector_t t1_joint_pos(onnx_conf_.actions_size);
  vector_t t1_joint_vel(onnx_conf_.actions_size);
  vector3_t t1_ang_vel;
  vector3_t t1_euler_xyz;

  {
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);
    for (size_t ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      t1_joint_pos(ii) = joint_state_data_.position[ii];
      t1_joint_vel(ii) = joint_state_data_.velocity[ii];
    }
  }
  {
    std::shared_lock<std::shared_mutex> lock(imu_mutex_);
    t1_ang_vel(0) = imu_data_.angular_velocity.x;
    t1_ang_vel(1) = imu_data_.angular_velocity.y;
    t1_ang_vel(2) = imu_data_.angular_velocity.z;
    quaternion_t quat;
    quat.x() = imu_data_.orientation.x;
    quat.y() = imu_data_.orientation.y;
    quat.z() = imu_data_.orientation.z;
    quat.w() = imu_data_.orientation.w;
    t1_euler_xyz = QuatToXyz(quat);
  }

  // ---- 2. 检测 zero 模式上升沿，触发记录 ----
  bool zero_entered = zero_mode_entered_.load(std::memory_order_acquire);

  if (zero_entered && !t1_logging_triggered_) {
    // 关闭之前未关闭的文件
    if (t1_joint_pos_file_.is_open()) { t1_joint_pos_file_.flush(); t1_joint_pos_file_.close(); }
    if (t1_joint_vel_file_.is_open()) { t1_joint_vel_file_.flush(); t1_joint_vel_file_.close(); }
    if (t1_imu_file_.is_open()) { t1_imu_file_.flush(); t1_imu_file_.close(); }
    fprintf(stderr, "[RLController] T1 triggered by zero mode entry\n");

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

    // T1-1: 关节零位 = joint_pos * dof_pos_scale（验证真机 zero 位是否为全零）
    std::string pos_path = t1_log_dir_ + "/t11_joint_pos_" + std::string(time_buf) + ".csv";
    t1_joint_pos_file_.open(pos_path);
    if (t1_joint_pos_file_.is_open()) {
      t1_joint_pos_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t1_joint_pos_file_ << ",pos_obs_" << name;
      }
      t1_joint_pos_file_ << "\n";
    }

    // T1-2: 关节速度 = joint_vel * dof_vel_scale
    std::string vel_path = t1_log_dir_ + "/t12_joint_vel_" + std::string(time_buf) + ".csv";
    t1_joint_vel_file_.open(vel_path);
    if (t1_joint_vel_file_.is_open()) {
      t1_joint_vel_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t1_joint_vel_file_ << ",vel_obs_" << name;
      }
      t1_joint_vel_file_ << "\n";
    }

    // T1-3: IMU = ang_vel * ang_vel_scale + euler * quat_scale
    std::string imu_path = t1_log_dir_ + "/t13_imu_" + std::string(time_buf) + ".csv";
    t1_imu_file_.open(imu_path);
    if (t1_imu_file_.is_open()) {
      t1_imu_file_ << "timestamp_ns,ang_vel_obs_x,ang_vel_obs_y,ang_vel_obs_z,euler_obs_x,euler_obs_y,euler_obs_z\n";
    }

    bool all_open = t1_joint_pos_file_.is_open() && t1_joint_vel_file_.is_open() && t1_imu_file_.is_open();
    if (all_open) {
      t1_logging_triggered_ = true;
      t1_log_count_ = 0;
      fprintf(stderr, "[RLController] T1 CSV logging triggered (3 files, max 40s @ 1000Hz)\n");
      fprintf(stderr, "  - T1-1 JointPos: %s\n", pos_path.c_str());
      fprintf(stderr, "  - T1-2 JointVel: %s\n", vel_path.c_str());
      fprintf(stderr, "  - T1-3 IMU:      %s\n", imu_path.c_str());
    } else {
      fprintf(stderr, "[RLController] ERROR: Failed to open one or more T1 log files\n");
    }
  }

  // ---- 3. 如果已触发，计算 obs pipeline 数据并记录 ----
  if (!t1_logging_triggered_ || t1_log_count_ >= t1_log_max_count_) {
    return;
  }

  // 计算与 ComputeObservation 中一致的 obs 值（当前帧，无历史）
  vector_t obs_joint_pos = t1_joint_pos * obs_scales_.dof_pos;
  vector_t obs_joint_vel = t1_joint_vel * obs_scales_.dof_vel;
  vector3_t obs_ang_vel = t1_ang_vel * obs_scales_.ang_vel;
  vector3_t obs_euler = t1_euler_xyz * obs_scales_.quat;

  auto now_ns = duration_cast<nanoseconds>(
      high_resolution_clock::now().time_since_epoch()).count();

  // T1-1: 关节零位偏差
  t1_joint_pos_file_ << now_ns;
  for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
    t1_joint_pos_file_ << "," << obs_joint_pos(ii);
  }
  t1_joint_pos_file_ << "\n";

  // T1-2: 关节速度
  t1_joint_vel_file_ << now_ns;
  for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
    t1_joint_vel_file_ << "," << obs_joint_vel(ii);
  }
  t1_joint_vel_file_ << "\n";

  // T1-3: IMU
  t1_imu_file_ << now_ns
               << "," << obs_ang_vel(0) << "," << obs_ang_vel(1) << "," << obs_ang_vel(2)
               << "," << obs_euler(0) << "," << obs_euler(1) << "," << obs_euler(2)
               << "\n";

  t1_log_count_++;
  if (t1_log_count_ % 10000 == 0) {
    fprintf(stderr, "[RLController] T1 logging progress: %d/%d frames\n", t1_log_count_, t1_log_max_count_);
  }

  if (t1_log_count_ >= t1_log_max_count_) {
    t1_joint_pos_file_.flush(); t1_joint_pos_file_.close();
    t1_joint_vel_file_.flush(); t1_joint_vel_file_.close();
    t1_imu_file_.flush(); t1_imu_file_.close();
    t1_logging_triggered_ = false;
    zero_mode_entered_.store(false, std::memory_order_release);
    fprintf(stderr, "[RLController] T1 CSV logging finished (%d frames, 40s)\n", t1_log_count_);
  }
}

void RLController::LogT2Data() {
  if (!t2_logging_enabled_) {
    return;
  }

  // ---- 检测 walk_leg 模式上升沿，触发记录 ----
  bool walk_entered = walk_leg_entered_.load(std::memory_order_acquire);

  if (walk_entered && !t2_logging_triggered_) {
    // 关闭之前未关闭的文件
    if (t2_gait_file_.is_open()) { t2_gait_file_.flush(); t2_gait_file_.close(); }
    if (t2_joint_file_.is_open()) { t2_joint_file_.flush(); t2_joint_file_.close(); }
    if (t2_pose_file_.is_open()) { t2_pose_file_.flush(); t2_pose_file_.close(); }
    if (t2_action_file_.is_open()) { t2_action_file_.flush(); t2_action_file_.close(); }

    // 重置步态检测辅助变量
    last_contact_state_[0] = false;
    last_contact_state_[1] = false;
    last_contact_time_[0] = 0.0;
    last_contact_time_[1] = 0.0;

    // 创建新的日志文件
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

    std::string gait_path = t2_log_dir_ + "/t22_gait_" + std::string(time_buf) + ".csv";
    t2_gait_file_.open(gait_path);
    if (t2_gait_file_.is_open()) {
      t2_gait_file_ << "timestamp_ns,left_contact,right_contact,cycle_time_ms\n";
    }

    std::string joint_path = t2_log_dir_ + "/t23_joint_" + std::string(time_buf) + ".csv";
    t2_joint_file_.open(joint_path);
    if (t2_joint_file_.is_open()) {
      t2_joint_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t2_joint_file_ << ",pos_" << name << ",vel_" << name << ",target_" << name;
      }
      t2_joint_file_ << "\n";
    }

    std::string pose_path = t2_log_dir_ + "/t24_pose_" + std::string(time_buf) + ".csv";
    t2_pose_file_.open(pose_path);
    if (t2_pose_file_.is_open()) {
      t2_pose_file_ << "timestamp_ns,euler_x,euler_y,euler_z,ang_vel_x,ang_vel_y,ang_vel_z,lin_vel_x,lin_vel_y,lin_vel_z\n";
    }

    std::string action_path = t2_log_dir_ + "/t25_action_" + std::string(time_buf) + ".csv";
    t2_action_file_.open(action_path);
    if (t2_action_file_.is_open()) {
      t2_action_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t2_action_file_ << ",action_" << name;
      }
      t2_action_file_ << ",clip_count\n";
    }

    bool all_open = t2_gait_file_.is_open() && t2_joint_file_.is_open() &&
                    t2_pose_file_.is_open() && t2_action_file_.is_open();
    if (all_open) {
      t2_logging_triggered_ = true;
      t2_log_count_ = 0;
      fprintf(stderr, "[RLController] T2 CSV logging triggered by walk_leg mode (max %d frames)\n", t2_log_max_count_);
      fprintf(stderr, "  - T2-2 Gait:   %s\n", gait_path.c_str());
      fprintf(stderr, "  - T2-3 Joint:  %s\n", joint_path.c_str());
      fprintf(stderr, "  - T2-4 Pose:   %s\n", pose_path.c_str());
      fprintf(stderr, "  - T2-5 Action: %s\n", action_path.c_str());
    } else {
      fprintf(stderr, "[RLController] ERROR: Failed to open one or more T2 log files\n");
    }
  }

  // ---- 如果未触发或已记满，直接返回 ----
  if (!t2_logging_triggered_ || t2_log_count_ >= t2_log_max_count_) {
    return;
  }

  auto now_ns = duration_cast<nanoseconds>(
      high_resolution_clock::now().time_since_epoch()).count();

  // ---- T2-2: 步态周期 ----
  {
    bool left_contact = DetectFootContact(0);
    bool right_contact = DetectFootContact(1);

    double cycle_time_ms = -1.0;
    if (left_contact && !last_contact_state_[0]) {
      double now_sec = now_ns / 1e9;
      if (last_contact_time_[0] > 0) {
        cycle_time_ms = (now_sec - last_contact_time_[0]) * 1000.0;
      }
      last_contact_time_[0] = now_sec;
    }

    t2_gait_file_ << now_ns << "," << left_contact << "," << right_contact
                  << "," << cycle_time_ms << "\n";

    last_contact_state_[0] = left_contact;
    last_contact_state_[1] = right_contact;
  }

  // ---- T2-3: 关节轨迹 ----
  {
    t2_joint_file_ << now_ns;
    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      double pos_target = actions_[ii] * walk_step_conf_.action_scale + joint_conf_.init_state(ii);
      pos_target = std::max(joint_conf_.pos_limit_lower(ii),
                           std::min(joint_conf_.pos_limit_upper(ii), pos_target));

      t2_joint_file_ << "," << propri_.joint_pos(ii)
                     << "," << propri_.joint_vel(ii)
                     << "," << pos_target;
    }
    t2_joint_file_ << "\n";
  }

  // ---- T2-4: 机身姿态 ----
  {
    t2_pose_file_ << now_ns
                  << "," << propri_.base_euler_xyz(0)
                  << "," << propri_.base_euler_xyz(1)
                  << "," << propri_.base_euler_xyz(2)
                  << "," << propri_.base_ang_vel(0)
                  << "," << propri_.base_ang_vel(1)
                  << "," << propri_.base_ang_vel(2)
                  << ",0.0,0.0,0.0\n";  // TODO: 真机需要订阅里程计 topic
  }

  // ---- T2-5: 网络输出 Action ----
  {
    int clip_count = 0;
    t2_action_file_ << now_ns;
    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      t2_action_file_ << "," << actions_[ii];
      if (std::abs(actions_[ii]) >= onnx_conf_.actions_clip - 1e-6) {
        clip_count++;
      }
    }
    t2_action_file_ << "," << clip_count << "\n";
  }

  t2_log_count_++;
  if (t2_log_count_ % 5000 == 0) {
    fprintf(stderr, "[RLController] T2 logging progress: %d/%d frames\n", t2_log_count_, t2_log_max_count_);
  }
  if (t2_log_count_ >= t2_log_max_count_) {
    t2_gait_file_.flush();
    t2_gait_file_.close();
    t2_joint_file_.flush();
    t2_joint_file_.close();
    t2_pose_file_.flush();
    t2_pose_file_.close();
    t2_action_file_.flush();
    t2_action_file_.close();
    t2_logging_triggered_ = false;
    walk_leg_entered_.store(false, std::memory_order_release);
    fprintf(stderr, "[RLController] T2 CSV logging finished (%d frames, 40s)\n", t2_log_count_);
  }
}

bool RLController::DetectFootContact(int foot_idx) {
  // ...
  // 真机可能需要:
  // 1. 力传感器数据
  // 2. 足端位置 + 速度阈值
  // 3. IMU 加速度特征

  // 请根据实际 joint_list 配置调整这些索引值
  int ankle_idx = (foot_idx == 0) ? 4 : 10;  // 需根据实际 joint_list 调整

  if (ankle_idx >= onnx_conf_.actions_size) {
    return false;  // 索引越界保护
  }

  // 速度阈值法：速度接近 0 认为接触
  double vel_threshold = 0.5;  // rad/s，可调
  return std::abs(propri_.joint_vel(ankle_idx)) < vel_threshold;
}

void RLController::LogT3Data() {
  if (!t3_logging_enabled_) {
    return;
  }

  // ---- 检测 walk_leg 模式上升沿，触发记录 ----
  bool walk_entered = walk_leg_entered_.load(std::memory_order_acquire);

  if (walk_entered && !t3_logging_triggered_) {
    if (t3_current_file_.is_open()) { t3_current_file_.flush(); t3_current_file_.close(); }

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

    std::string current_path = t3_log_dir_ + "/t3_current_" + std::string(time_buf) + ".csv";
    fprintf(stderr, "[RLController] T3 attempting to open file: %s\n", current_path.c_str());
    t3_current_file_.open(current_path);
    if (t3_current_file_.is_open()) {
      t3_current_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t3_current_file_ << ",current_" << name << ",pos_" << name
                         << ",vel_" << name << ",target_" << name;
      }
      t3_current_file_ << "\n";

      t3_logging_triggered_ = true;
      t3_log_count_ = 0;
      fprintf(stderr, "[RLController] T3 CSV logging triggered by walk_leg mode (max %d frames, 40s)\n", t3_log_max_count_);
      fprintf(stderr, "  - T3 Current: %s\n", current_path.c_str());
    } else {
      fprintf(stderr, "[RLController] ERROR: Failed to open T3 log file: %s\n", current_path.c_str());
    }
  }

  // ---- 如果未触发或已记满，直接返回 ----
  if (!t3_logging_triggered_ || t3_log_count_ >= t3_log_max_count_) {
    return;
  }

  auto now_ns = duration_cast<nanoseconds>(
      high_resolution_clock::now().time_since_epoch()).count();

  // ---- T3: 电机电流监测 ----
  {
    t3_current_file_ << now_ns;

    // 从 joint_state_data_.effort 获取电流/力矩数据
    // 注意：effort 字段可能是力矩(Nm)或电流(A)，取决于硬件接口
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);

    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      double current = joint_state_data_.effort[ii];
      double pos_target = actions_[ii] * walk_step_conf_.action_scale + joint_conf_.init_state(ii);

      pos_target = std::max(joint_conf_.pos_limit_lower(ii),
                           std::min(joint_conf_.pos_limit_upper(ii), pos_target));

      t3_current_file_ << "," << current
                       << "," << propri_.joint_pos(ii)
                       << "," << propri_.joint_vel(ii)
                       << "," << pos_target;
    }
    t3_current_file_ << "\n";
  }

  t3_log_count_++;
  if (t3_log_count_ % 5000 == 0) {
    fprintf(stderr, "[RLController] T3 logging progress: %d/%d frames\n", t3_log_count_, t3_log_max_count_);
  }
  if (t3_log_count_ >= t3_log_max_count_) {
    t3_current_file_.flush();
    t3_current_file_.close();
    t3_logging_triggered_ = false;
    walk_leg_entered_.store(false, std::memory_order_release);
    fprintf(stderr, "[RLController] T3 CSV logging finished (%d frames, 40s)\n", t3_log_count_);
  }
}

void RLController::LogT4RawSensorData() {
  if (!t4_logging_enabled_) {
    return;
  }

  // ---- 检测 walk_leg 模式上升沿，触发记录 ----
  bool walk_entered = walk_leg_entered_.load(std::memory_order_acquire);

  if (walk_entered && !t4_logging_triggered_) {
    // 关闭之前未关闭的文件
    if (t4_raw_joint_pos_file_.is_open()) { t4_raw_joint_pos_file_.flush(); t4_raw_joint_pos_file_.close(); }
    if (t4_raw_joint_vel_file_.is_open()) { t4_raw_joint_vel_file_.flush(); t4_raw_joint_vel_file_.close(); }
    if (t4_raw_motor_current_file_.is_open()) { t4_raw_motor_current_file_.flush(); t4_raw_motor_current_file_.close(); }
    if (t4_raw_imu_quat_file_.is_open()) { t4_raw_imu_quat_file_.flush(); t4_raw_imu_quat_file_.close(); }
    if (t4_raw_imu_gyro_file_.is_open()) { t4_raw_imu_gyro_file_.flush(); t4_raw_imu_gyro_file_.close(); }
    if (t4_raw_imu_accel_file_.is_open()) { t4_raw_imu_accel_file_.flush(); t4_raw_imu_accel_file_.close(); }

    // 创建时间戳文件名
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

    // T4-1: 原始关节位置
    std::string pos_path = t4_log_dir_ + "/t4_raw_joint_pos_" + std::string(time_buf) + ".csv";
    t4_raw_joint_pos_file_.open(pos_path);
    if (t4_raw_joint_pos_file_.is_open()) {
      t4_raw_joint_pos_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t4_raw_joint_pos_file_ << "," << name;
      }
      t4_raw_joint_pos_file_ << "\n";
    }

    // T4-2: 原始关节速度
    std::string vel_path = t4_log_dir_ + "/t4_raw_joint_vel_" + std::string(time_buf) + ".csv";
    t4_raw_joint_vel_file_.open(vel_path);
    if (t4_raw_joint_vel_file_.is_open()) {
      t4_raw_joint_vel_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t4_raw_joint_vel_file_ << "," << name;
      }
      t4_raw_joint_vel_file_ << "\n";
    }

    // T4-3: 原始电机电流
    std::string current_path = t4_log_dir_ + "/t4_raw_motor_current_" + std::string(time_buf) + ".csv";
    t4_raw_motor_current_file_.open(current_path);
    if (t4_raw_motor_current_file_.is_open()) {
      t4_raw_motor_current_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t4_raw_motor_current_file_ << "," << name;
      }
      t4_raw_motor_current_file_ << "\n";
    }

    // T4-4: 原始IMU四元数
    std::string quat_path = t4_log_dir_ + "/t4_raw_imu_quat_" + std::string(time_buf) + ".csv";
    t4_raw_imu_quat_file_.open(quat_path);
    if (t4_raw_imu_quat_file_.is_open()) {
      t4_raw_imu_quat_file_ << "timestamp_ns,quat_w,quat_x,quat_y,quat_z\n";
    }

    // T4-5: 原始IMU角速度
    std::string gyro_path = t4_log_dir_ + "/t4_raw_imu_gyro_" + std::string(time_buf) + ".csv";
    t4_raw_imu_gyro_file_.open(gyro_path);
    if (t4_raw_imu_gyro_file_.is_open()) {
      t4_raw_imu_gyro_file_ << "timestamp_ns,gyro_x,gyro_y,gyro_z\n";
    }

    // T4-6: 原始IMU加速度
    std::string accel_path = t4_log_dir_ + "/t4_raw_imu_accel_" + std::string(time_buf) + ".csv";
    t4_raw_imu_accel_file_.open(accel_path);
    if (t4_raw_imu_accel_file_.is_open()) {
      t4_raw_imu_accel_file_ << "timestamp_ns,accel_x,accel_y,accel_z\n";
    }

    bool all_open = t4_raw_joint_pos_file_.is_open() && t4_raw_joint_vel_file_.is_open() &&
                    t4_raw_motor_current_file_.is_open() && t4_raw_imu_quat_file_.is_open() &&
                    t4_raw_imu_gyro_file_.is_open() && t4_raw_imu_accel_file_.is_open();
    if (all_open) {
      t4_logging_triggered_ = true;
      t4_log_count_ = 0;
      fprintf(stderr, "[RLController] T4 raw sensor CSV logging triggered by walk_leg mode (6 files, max %d frames @ 1000Hz)\n", t4_log_max_count_);
      fprintf(stderr, "  - T4-1 RawJointPos:     %s\n", pos_path.c_str());
      fprintf(stderr, "  - T4-2 RawJointVel:     %s\n", vel_path.c_str());
      fprintf(stderr, "  - T4-3 RawMotorCurrent: %s\n", current_path.c_str());
      fprintf(stderr, "  - T4-4 RawIMUQuat:      %s\n", quat_path.c_str());
      fprintf(stderr, "  - T4-5 RawIMUGyro:      %s\n", gyro_path.c_str());
      fprintf(stderr, "  - T4-6 RawIMUAccel:     %s\n", accel_path.c_str());
    } else {
      fprintf(stderr, "[RLController] ERROR: Failed to open one or more T4 log files\n");
    }
  }

  // ---- 如果未触发或已记满，直接返回 ----
  if (!t4_logging_triggered_ || t4_log_count_ >= t4_log_max_count_) {
    return;
  }

  auto now_ns = duration_cast<nanoseconds>(
      high_resolution_clock::now().time_since_epoch()).count();

  // ---- T4-1: 原始关节位置 (rad) ----
  {
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);
    t4_raw_joint_pos_file_ << now_ns;
    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      t4_raw_joint_pos_file_ << "," << joint_state_data_.position[ii];
    }
    t4_raw_joint_pos_file_ << "\n";
  }

  // ---- T4-2: 原始关节速度 (rad/s) ----
  {
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);
    t4_raw_joint_vel_file_ << now_ns;
    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      t4_raw_joint_vel_file_ << "," << joint_state_data_.velocity[ii];
    }
    t4_raw_joint_vel_file_ << "\n";
  }

  // ---- T4-3: 原始电机电流 (A 或 Nm，取决于硬件接口) ----
  {
    std::shared_lock<std::shared_mutex> lock(joint_state_mutex_);
    t4_raw_motor_current_file_ << now_ns;
    for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
      t4_raw_motor_current_file_ << "," << joint_state_data_.effort[ii];
    }
    t4_raw_motor_current_file_ << "\n";
  }

  // ---- T4-4: 原始IMU四元数 (w,x,y,z) ----
  {
    std::shared_lock<std::shared_mutex> lock(imu_mutex_);
    t4_raw_imu_quat_file_ << now_ns
                          << "," << imu_data_.orientation.w
                          << "," << imu_data_.orientation.x
                          << "," << imu_data_.orientation.y
                          << "," << imu_data_.orientation.z
                          << "\n";
  }

  // ---- T4-5: 原始IMU角速度 (rad/s) ----
  {
    std::shared_lock<std::shared_mutex> lock(imu_mutex_);
    t4_raw_imu_gyro_file_ << now_ns
                          << "," << imu_data_.angular_velocity.x
                          << "," << imu_data_.angular_velocity.y
                          << "," << imu_data_.angular_velocity.z
                          << "\n";
  }

  // ---- T4-6: 原始IMU加速度 (m/s^2) ----
  {
    std::shared_lock<std::shared_mutex> lock(imu_mutex_);
    t4_raw_imu_accel_file_ << now_ns
                           << "," << imu_data_.linear_acceleration.x
                           << "," << imu_data_.linear_acceleration.y
                           << "," << imu_data_.linear_acceleration.z
                           << "\n";
  }

  t4_log_count_++;
  if (t4_log_count_ % 10000 == 0) {
    fprintf(stderr, "[RLController] T4 raw sensor logging progress: %d/%d frames\n", t4_log_count_, t4_log_max_count_);
  }

  if (t4_log_count_ >= t4_log_max_count_) {
    t4_raw_joint_pos_file_.flush(); t4_raw_joint_pos_file_.close();
    t4_raw_joint_vel_file_.flush(); t4_raw_joint_vel_file_.close();
    t4_raw_motor_current_file_.flush(); t4_raw_motor_current_file_.close();
    t4_raw_imu_quat_file_.flush(); t4_raw_imu_quat_file_.close();
    t4_raw_imu_gyro_file_.flush(); t4_raw_imu_gyro_file_.close();
    t4_raw_imu_accel_file_.flush(); t4_raw_imu_accel_file_.close();
    t4_logging_triggered_ = false;
    fprintf(stderr, "[RLController] T4 raw sensor CSV logging finished (%d frames, 40s @ 1000Hz)\n", t4_log_count_);
  }
}

} // namespace xyber_x1_infer::