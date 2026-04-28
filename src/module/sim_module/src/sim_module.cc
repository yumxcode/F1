// Copyright (c) 2023, AgiBot Inc.
// All rights reserved.
#include "sim_module/sim_module.h"
#include <yaml-cpp/yaml.h>
#include "aimrt_module_ros2_interface/channel/ros2_channel.h"

namespace xyber_x1_infer::sim_module {

bool SimModule::Initialize(aimrt::CoreRef core) {
  // Save aimrt framework handle
  start_time_ = high_resolution_clock::now();

  core_ = core;
  auto file_path = core_.GetConfigurator().GetConfigFilePath();
  if (file_path.empty()) {
    AIMRT_ERROR("Init failed, [file_path] Empty");
    return false;
  }
  try {
    YAML::Node cfg_node = YAML::LoadFile(file_path.data());
    filename_ = cfg_node["model_file"].as<std::string>();

    joint_cmd_sub_ = core_.GetChannelHandle().GetSubscriber(cfg_node["sub_joint_cmd_topic"].as<std::string>());
    aimrt::channel::Subscribe<my_ros2_proto::msg::JointCommand>(joint_cmd_sub_, std::bind(&SimModule::CmdCallback, this, std::placeholders::_1));
    imu_data_pub_ = core_.GetChannelHandle().GetPublisher(cfg_node["pub_imu_data_topic"].as<std::string>());
    aimrt::channel::RegisterPublishType<sensor_msgs::msg::Imu>(imu_data_pub_);
    joint_state_pub_ =core_.GetChannelHandle().GetPublisher(cfg_node["pub_joint_state_topic"].as<std::string>());
    aimrt::channel::RegisterPublishType<sensor_msgs::msg::JointState>(joint_state_pub_);

    // subscribe to walk_mode trigger for GRF logging
    walk_mode_sub_ = core_.GetChannelHandle().GetSubscriber("/walk_mode");
    aimrt::channel::Subscribe<std_msgs::msg::Float32>(walk_mode_sub_,
      [this](const std::shared_ptr<const std_msgs::msg::Float32>& /*msg*/) {
        grf_walk_entered_.store(true, std::memory_order_release);
        fprintf(stderr, "[SimModule] /walk_mode received, GRF logging armed\n");
      });

    render_executor_ = core_.GetExecutorManager().GetExecutor("sim_render_thread");

    AIMRT_INFO("Init succeeded.");
    return true;
  } catch (const std::exception& e) {
    AIMRT_ERROR("Exit MainLoop with exception, {}", e.what());
    return false;
  }
}

bool SimModule::Start() {
  mjv_defaultCamera(&cam_);
  mjv_defaultOption(&opt_);
  mjv_defaultPerturb(&pert_);

  // Render thread
  render_executor_.Execute([this]() {
    sim_ = std::make_shared<mj::Simulate>(std::make_unique<mj::GlfwAdapter>(), &cam_, &opt_, &pert_, false);
    sim_->LoadMessage(filename_.data());
    const int kErrorLength = 1024;
    char loadError[kErrorLength] = "";
    m_ = mj_loadXML(filename_.data(), nullptr, loadError, kErrorLength);
    mju::strcpy_arr(sim_->load_error, loadError);
    if (m_) {
      const std::unique_lock<std::recursive_mutex> lock(sim_->mtx);
      d_ = mj_makeData(m_);
    }
    is_render_thread_running_ = true;
    sim_->RenderLoop();
  });

  while (!is_render_thread_running_) {
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  if (d_) {
    sim_->Load(m_, d_, filename_.data());
    const std::unique_lock<std::recursive_mutex> lock(sim_->mtx);
    mj_forward(m_, d_);
    free(ctrl_noise_);
    ctrl_noise_ = static_cast<mjtNum*>(malloc(sizeof(mjtNum)*m_->nu));
    mju_zero(ctrl_noise_, m_->nu);
  } else {
    sim_->LoadMessageClear();
  }

  joint_names_.clear();
  for (int i = 0; i < m_->njnt; ++i) {
    if (m_->jnt_type[i] == mjJNT_FREE) {
      continue;
    }
    const char* joint_name = mj_id2name(m_, mjOBJ_JOINT, i);
    joint_names_.push_back(std::string(joint_name));
  }

  // init pid
  target_q_.resize(joint_names_.size());
  target_dq_.resize(joint_names_.size());
  target_tq_.resize(joint_names_.size());
  kp_.resize(joint_names_.size());
  kd_.resize(joint_names_.size());
  motor_torque_.resize(joint_names_.size());

  // ---- GRF logging: cache geom IDs ----
  grf_log_dir_ = "test_logs/data_csv/test_friction";
  std::filesystem::create_directories(grf_log_dir_);
  floor_geom_id_ = mj_name2id(m_, mjOBJ_GEOM, "floor");
  int left_ankle_body  = mj_name2id(m_, mjOBJ_BODY, "link_left_ankle_roll");
  int right_ankle_body = mj_name2id(m_, mjOBJ_BODY, "link_right_ankle_roll");
  for (int g = 0; g < m_->ngeom; g++) {
    if (m_->geom_contype[g] == 0) continue;  // skip non-collision geoms
    if (m_->geom_bodyid[g] == left_ankle_body)
      left_foot_geoms_.insert(g);
    if (m_->geom_bodyid[g] == right_ankle_body)
      right_foot_geoms_.insert(g);
  }
  grf_logging_enabled_ = false;  // [开关] true=启用, false=禁用
  fprintf(stderr, "[SimModule] GRF logging %s (geom cache: floor=%d, left=%zu, right=%zu geoms)\n",
          grf_logging_enabled_ ? "ENABLED" : "DISABLED",
          floor_geom_id_, left_foot_geoms_.size(), right_foot_geoms_.size());

  AIMRT_INFO("Started succeeded.");
  return true;
}

void SimModule::Shutdown() {
  if (grf_file_.is_open()) { grf_file_.flush(); grf_file_.close(); }
  free(ctrl_noise_);
  mj_deleteData(d_);
  mj_deleteModel(m_);
  AIMRT_INFO("Shutdown succeeded.");
}

void SimModule::CmdCallback(const std::shared_ptr<const my_ros2_proto::msg::JointCommand>& msg) {
  sensor_msgs::msg::Imu imu_data_msg;
  sensor_msgs::msg::JointState joint_states_msg;

  auto elapsed = high_resolution_clock::now() - start_time_;
  if (elapsed <= milliseconds(3000)) {
    return;
  }

  const std::unique_lock<std::recursive_mutex> lock(sim_->mtx);
  WriteMotorCmd(*msg);
  mj_step(m_, d_);
  if (grf_logging_enabled_) {
    LogGRFData();
  }
  ReadSensorData(imu_data_msg, joint_states_msg);

  aimrt::channel::Publish<sensor_msgs::msg::Imu>(imu_data_pub_, imu_data_msg);
  aimrt::channel::Publish<sensor_msgs::msg::JointState>(joint_state_pub_, joint_states_msg);
}

void SimModule::ReadSensorData(sensor_msgs::msg::Imu& imu_data, sensor_msgs::msg::JointState& joint_state) {
  auto duration = high_resolution_clock::now().time_since_epoch();
  auto sec = duration_cast<seconds>(duration);
  auto nanosec = duration_cast<nanoseconds>(duration - sec);

  imu_data.orientation.w = d_->sensordata[0];
  imu_data.orientation.x = d_->sensordata[1];
  imu_data.orientation.y = d_->sensordata[2];
  imu_data.orientation.z = d_->sensordata[3];
  imu_data.angular_velocity.x = d_->sensordata[4];
  imu_data.angular_velocity.y = d_->sensordata[5];
  imu_data.angular_velocity.z = d_->sensordata[6];
  imu_data.linear_acceleration.x = d_->sensordata[13];
  imu_data.linear_acceleration.y = d_->sensordata[14];
  imu_data.linear_acceleration.z = d_->sensordata[15];
  imu_data.header.stamp.sec = sec.count();
  imu_data.header.stamp.nanosec = nanosec.count();

  joint_state.name = joint_names_;
  joint_state.position.resize(joint_names_.size(), 0.0);
  joint_state.velocity.resize(joint_names_.size(), 0.0);
  joint_state.effort.resize(joint_names_.size(), 0.0);
  memcpy((void*)joint_state.position.data(), d_->qpos+7, joint_names_.size() * sizeof(double));
  memcpy((void*)joint_state.velocity.data(), d_->qvel+6, joint_names_.size() * sizeof(double));
  memcpy((void*)joint_state.effort.data(), d_->qfrc_actuator+6, joint_names_.size() * sizeof(double));
  joint_state.header.stamp.sec = sec.count();
  joint_state.header.stamp.nanosec = nanosec.count();
}

void SimModule::WriteMotorCmd(my_ros2_proto::msg::JointCommand cmd) {
  for (size_t ii = 0; ii < cmd.name.size(); ii++) {
    joint_state_index_map_[cmd.name[ii]] = ii;
  }

  for (size_t ii = 0; ii < joint_names_.size(); ++ii) {
    int index = joint_state_index_map_[joint_names_[ii]];
    target_q_(ii) = cmd.position[index];
    target_dq_(ii) = cmd.velocity[index];
    target_tq_(ii) = cmd.effort[index];
    kp_(ii) = cmd.stiffness[index];
    kd_(ii) = cmd.damping[index];
  }
  array_t q = Eigen::Map<array_t>(d_->qpos + 7, joint_names_.size());
  array_t dq = Eigen::Map<array_t>(d_->qvel + 6, joint_names_.size());
  motor_torque_ = target_tq_ + (target_q_ - q) * kp_ + (target_dq_ - dq) * kd_;
  d_->ctrl = motor_torque_.data();

  // 添加控制噪声
  if (sim_->ctrl_noise_std) {
    mjtNum rate = mju_exp(-m_->opt.timestep / mju_max(sim_->ctrl_noise_rate, mjMINVAL));
    mjtNum scale = sim_->ctrl_noise_std * mju_sqrt(1-rate*rate);
    for (int i=0; i<m_->nu; i++) {
      ctrl_noise_[i] = rate * ctrl_noise_[i] + scale * mju_standardNormal(nullptr);
      d_->ctrl[i] += ctrl_noise_[i];
    }
  }
}

void SimModule::LogGRFData() {
  // ---- detect walk_leg rising edge, open CSV ----
  bool walk_entered = grf_walk_entered_.load(std::memory_order_acquire);

  if (walk_entered && !grf_logging_triggered_) {
    if (grf_file_.is_open()) { grf_file_.flush(); grf_file_.close(); }

    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);
    std::tm tm_now{};
    localtime_r(&time_t_now, &tm_now);
    char time_buf[64];
    std::strftime(time_buf, sizeof(time_buf), "%Y%m%d_%H%M%S", &tm_now);

    std::string path = grf_log_dir_ + "/grf_" + std::string(time_buf) + ".csv";
    grf_file_.open(path);
    if (grf_file_.is_open()) {
      grf_file_ << "timestamp_ns,sim_time"
                << ",left_contact_count,left_Fn,left_Fx,left_Fy,left_Ft,left_pos_x,left_pos_y,left_pos_z"
                << ",right_contact_count,right_Fn,right_Fx,right_Fy,right_Ft,right_pos_x,right_pos_y,right_pos_z"
                << "\n";
      grf_logging_triggered_ = true;
      grf_log_count_ = 0;
      fprintf(stderr, "[SimModule] GRF CSV logging started: %s (max %d frames, %.0fs)\n",
              path.c_str(), grf_log_max_count_, grf_log_max_count_ * 0.001);
    } else {
      fprintf(stderr, "[SimModule] ERROR: Failed to open GRF log: %s\n", path.c_str());
    }
  }

  if (!grf_logging_triggered_ || grf_log_count_ >= grf_log_max_count_) {
    return;
  }

  // ---- accumulate contact forces per foot ----
  double left_Fn = 0, left_Fx = 0, left_Fy = 0;
  double left_px = 0, left_py = 0, left_pz = 0;
  int left_count = 0;

  double right_Fn = 0, right_Fx = 0, right_Fy = 0;
  double right_px = 0, right_py = 0, right_pz = 0;
  int right_count = 0;

  for (int i = 0; i < d_->ncon; i++) {
    const mjContact& c = d_->contact[i];
    if (c.exclude) continue;
    if (c.efc_address < 0) continue;

    int g0 = c.geom[0], g1 = c.geom[1];

    // determine which foot (if any) is involved, and ensure other geom is floor
    bool is_left = false, is_right = false;
    if ((left_foot_geoms_.count(g0) && g1 == floor_geom_id_) ||
        (left_foot_geoms_.count(g1) && g0 == floor_geom_id_)) {
      is_left = true;
    }
    if ((right_foot_geoms_.count(g0) && g1 == floor_geom_id_) ||
        (right_foot_geoms_.count(g1) && g0 == floor_geom_id_)) {
      is_right = true;
    }
    if (!is_left && !is_right) continue;

    // extract 6D force in contact frame: [Fn, Ft1, Ft2, torque...]
    mjtNum result[6] = {0};
    mj_contactForce(m_, d_, i, result);

    if (is_left) {
      left_Fn += result[0];
      left_Fx += result[1];
      left_Fy += result[2];
      left_px += c.pos[0];
      left_py += c.pos[1];
      left_pz += c.pos[2];
      left_count++;
    }
    if (is_right) {
      right_Fn += result[0];
      right_Fx += result[1];
      right_Fy += result[2];
      right_px += c.pos[0];
      right_py += c.pos[1];
      right_pz += c.pos[2];
      right_count++;
    }
  }

  // average contact position
  if (left_count > 0)  { left_px  /= left_count;  left_py  /= left_count;  left_pz  /= left_count; }
  if (right_count > 0) { right_px /= right_count; right_py /= right_count; right_pz /= right_count; }

  double left_Ft  = std::sqrt(left_Fx * left_Fx + left_Fy * left_Fy);
  double right_Ft = std::sqrt(right_Fx * right_Fx + right_Fy * right_Fy);

  // ---- write CSV row ----
  auto now_ns = duration_cast<nanoseconds>(
      high_resolution_clock::now().time_since_epoch()).count();

  grf_file_ << now_ns << "," << d_->time
            << "," << left_count  << "," << left_Fn  << "," << left_Fx  << "," << left_Fy  << "," << left_Ft
            << "," << left_px  << "," << left_py  << "," << left_pz
            << "," << right_count << "," << right_Fn << "," << right_Fx << "," << right_Fy << "," << right_Ft
            << "," << right_px << "," << right_py << "," << right_pz
            << "\n";

  grf_log_count_++;

  // progress print every 5000 frames (~5s)
  if (grf_log_count_ % 5000 == 0) {
    double pct = 100.0 * grf_log_count_ / grf_log_max_count_;
    fprintf(stderr, "[SimModule] GRF progress: %d/%d (%.0f%%)\n",
            grf_log_count_, grf_log_max_count_, pct);
  }

  // ---- finish ----
  if (grf_log_count_ >= grf_log_max_count_) {
    grf_file_.flush();
    grf_file_.close();
    grf_logging_triggered_ = false;
    grf_walk_entered_.store(false, std::memory_order_release);
    fprintf(stderr, "[SimModule] GRF CSV logging finished (%d frames, %.0fs)\n",
            grf_log_count_, grf_log_count_ * 0.001);
  }
}

}  // namespace xyber_x1_infer::sim_module
