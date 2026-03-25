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

  // ---- T1 静态测试 CSV 日志初始化 ----
  {
    t1_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t1_log_dir_);

    // T1 改为触发式记录，不在初始化时打开文件
    t1_log_max_count_ = 40000;  // 40s * 1000Hz
    t1_log_count_ = 0;
    t1_logging_enabled_ = true;  // 启用功能，但等待触发
    t1_logging_triggered_ = false;
    t1_last_cmd_zero_ = false;

    fprintf(stderr, "[RLController] T1 CSV logging enabled (waiting for joystick zero trigger, max 40s)\n");
  }
  // ---- T1 日志初始化结束 ----

  // ---- T2 测试 CSV 日志初始化 ----
  {
    t2_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t2_log_dir_);

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

    // T2-2: 步态周期
    std::string gait_path = t2_log_dir_ + "/t22_gait_" + std::string(time_buf) + ".csv";
    t2_gait_file_.open(gait_path);
    if (t2_gait_file_.is_open()) {
      t2_gait_file_ << "timestamp_ns,left_contact,right_contact,cycle_time_ms\n";
    }

    // T2-3: 关节轨迹
    std::string joint_path = t2_log_dir_ + "/t23_joint_" + std::string(time_buf) + ".csv";
    t2_joint_file_.open(joint_path);
    if (t2_joint_file_.is_open()) {
      t2_joint_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t2_joint_file_ << ",pos_" << name << ",vel_" << name << ",target_" << name;
      }
      t2_joint_file_ << "\n";
    }

    // T2-4: 机身姿态
    std::string pose_path = t2_log_dir_ + "/t24_pose_" + std::string(time_buf) + ".csv";
    t2_pose_file_.open(pose_path);
    if (t2_pose_file_.is_open()) {
      t2_pose_file_ << "timestamp_ns,euler_x,euler_y,euler_z,ang_vel_x,ang_vel_y,ang_vel_z,lin_vel_x,lin_vel_y,lin_vel_z\n";
    }

    // T2-5: 网络输出 Action
    std::string action_path = t2_log_dir_ + "/t25_action_" + std::string(time_buf) + ".csv";
    t2_action_file_.open(action_path);
    if (t2_action_file_.is_open()) {
      t2_action_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t2_action_file_ << ",action_" << name;
      }
      t2_action_file_ << ",clip_count\n";
    }

    // 20s * (1000Hz / decimation) 帧
    t2_log_max_count_ = 20 * (1000 / walk_step_conf_.decimation);
    t2_log_count_ = 0;
    t2_logging_enabled_ = t2_gait_file_.is_open() && t2_joint_file_.is_open() &&
                          t2_pose_file_.is_open() && t2_action_file_.is_open();

    // 初始化步态检测辅助变量
    last_contact_state_[0] = false;
    last_contact_state_[1] = false;
    last_contact_time_[0] = 0.0;
    last_contact_time_[1] = 0.0;

    if (t2_logging_enabled_) {
      fprintf(stderr, "[RLController] T2 CSV logging started (max %d frames)\n", t2_log_max_count_);
      fprintf(stderr, "  - T2-2 Gait:   %s\n", gait_path.c_str());
      fprintf(stderr, "  - T2-3 Joint:  %s\n", joint_path.c_str());
      fprintf(stderr, "  - T2-4 Pose:   %s\n", pose_path.c_str());
      fprintf(stderr, "  - T2-5 Action: %s\n", action_path.c_str());
    }
  }
  // ---- T2 日志初始化结束 ----

  // ---- T3 测试 CSV 日志初始化 ----
  {
    t3_log_dir_ = "test_logs/data_csv";
    std::filesystem::create_directories(t3_log_dir_);

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

    // T3: 电机电流监测
    std::string current_path = t3_log_dir_ + "/t3_current_" + std::string(time_buf) + ".csv";
    t3_current_file_.open(current_path);
    if (t3_current_file_.is_open()) {
      t3_current_file_ << "timestamp_ns";
      for (const auto& name : joint_names_) {
        t3_current_file_ << ",current_" << name << ",pos_" << name
                         << ",vel_" << name << ",target_" << name;
      }
      t3_current_file_ << "\n";
    }

    // 30s * (1000Hz / decimation) 帧
    t3_log_max_count_ = 30 * (1000 / walk_step_conf_.decimation);
    t3_log_count_ = 0;
    t3_logging_enabled_ = t3_current_file_.is_open();

    if (t3_logging_enabled_) {
      fprintf(stderr, "[RLController] T3 CSV logging started (max %d frames)\n", t3_log_max_count_);
      fprintf(stderr, "  - T3 Current: %s\n", current_path.c_str());
    }
  }
  // ---- T3 日志初始化结束 ----

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

  // ---- T1 数据采集（进入 zero 模式触发） ----
  if (t1_logging_enabled_) {
    // 检测进入 zero 模式的上升沿
    bool zero_entered = zero_mode_entered_.load(std::memory_order_acquire);
    
    if (zero_entered && !t1_logging_triggered_) {
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
      
      std::string log_path = t1_log_dir_ + "/t1_static_" + std::string(time_buf) + ".csv";
      t1_log_file_.open(log_path);
      if (t1_log_file_.is_open()) {
        // 写入表头
        t1_log_file_ << "timestamp_ns";
        for (const auto& name : joint_names_) {
          t1_log_file_ << ",pos_" << name << ",vel_" << name;
        }
        t1_log_file_ << ",ang_vel_x,ang_vel_y,ang_vel_z";
        t1_log_file_ << ",euler_x,euler_y,euler_z";
        t1_log_file_ << "\n";
        
        // 写入 init_state 参考行
        t1_log_file_ << "# init_state";
        for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
          t1_log_file_ << "," << joint_conf_.init_state(ii) << ",0";
        }
        t1_log_file_ << ",0,0,0,0,0,0\n";
        
        t1_logging_triggered_ = true;
        t1_log_count_ = 0;
        fprintf(stderr, "[RLController] T1 CSV logging triggered by ZERO mode (max 40s)\n");
        fprintf(stderr, "  - T1 Static: %s\n", log_path.c_str());
      }
    }
    
    // 如果已触发且文件打开，记录数据
    if (t1_logging_triggered_ && t1_log_file_.is_open() && t1_log_count_ < t1_log_max_count_) {
      auto now_ns = duration_cast<nanoseconds>(
          high_resolution_clock::now().time_since_epoch()).count();
      t1_log_file_ << now_ns;
      for (int ii = 0; ii < onnx_conf_.actions_size; ++ii) {
        t1_log_file_ << "," << propri_.joint_pos(ii)
                     << "," << propri_.joint_vel(ii);
      }
      t1_log_file_ << "," << propri_.base_ang_vel(0)
                   << "," << propri_.base_ang_vel(1)
                   << "," << propri_.base_ang_vel(2);
      t1_log_file_ << "," << propri_.base_euler_xyz(0)
                   << "," << propri_.base_euler_xyz(1)
                   << "," << propri_.base_euler_xyz(2);
      t1_log_file_ << "\n";
      t1_log_count_++;
      
      if (t1_log_count_ >= t1_log_max_count_) {
        t1_log_file_.flush();
        t1_log_file_.close();
        t1_logging_triggered_ = false;
        zero_mode_entered_.store(false, std::memory_order_release);  // 重置标志
        fprintf(stderr, "[RLController] T1 CSV logging finished (%d frames, 40s)\n", t1_log_count_);
      }
    }
  }
  // ---- T1 数据采集结束 ----
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

void RLController::LogT2Data() {
  if (t2_log_count_ >= t2_log_max_count_) {
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
  if (t2_log_count_ >= t2_log_max_count_) {
    t2_gait_file_.flush();
    t2_gait_file_.close();
    t2_joint_file_.flush();
    t2_joint_file_.close();
    t2_pose_file_.flush();
    t2_pose_file_.close();
    t2_action_file_.flush();
    t2_action_file_.close();
    t2_logging_enabled_ = false;
    fprintf(stderr, "[RLController] T2 CSV logging finished (%d frames)\n", t2_log_count_);
  }
}

bool RLController::DetectFootContact(int foot_idx) {
  // 简化版：基于踝关节速度判断接触
  // foot_idx: 0=left, 1=right
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
  if (t3_log_count_ >= t3_log_max_count_) {
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
  if (t3_log_count_ >= t3_log_max_count_) {
    t3_current_file_.flush();
    t3_current_file_.close();
    t3_logging_enabled_ = false;
    fprintf(stderr, "[RLController] T3 CSV logging finished (%d frames)\n", t3_log_count_);
  }
}

} // namespace xyber_x1_infer::