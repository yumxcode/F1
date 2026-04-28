// Copyright (c) 2023, AgiBot Inc.
// All rights reserved.
#pragma once
#include <chrono>
#include <cstdio>
#include <cstring>
#include <eigen3/Eigen/Core>
#include <fstream>
#include <filesystem>
#include <mutex>
#include <set>
#include <thread>
#include <vector>
#include <eigen3/Eigen/Core>

#include "sim_module/simulate.h"
#include "sim_module/glfw_adapter.h"
#include "sim_module/simulate.h"
#include "sim_module/array_safety.h"

#include "aimrt_module_cpp_interface/module_base.h"
#include "my_ros2_proto/msg/joint_command.hpp"
#include <std_msgs/msg/float32.hpp>
#include <std_msgs/msg/empty.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <sensor_msgs/msg/joint_state.hpp> 


extern "C" {
#include <sys/errno.h>
#include <unistd.h>
}

using array_t = Eigen::Array<double, Eigen::Dynamic, 1>;
using namespace std::chrono;
namespace mj = ::mujoco;
namespace mju = ::mujoco::sample_util;

namespace xyber_x1_infer::sim_module {

class SimModule : public aimrt::ModuleBase {
 public:
  SimModule() = default;
  ~SimModule() override = default;

  [[nodiscard]] aimrt::ModuleInfo Info() const override {
    return aimrt::ModuleInfo{.name = "SimModule"};
  }

  bool Initialize(aimrt::CoreRef core) override;
  bool Start() override;
  void Shutdown() override;

 private:
  auto GetLogger() { return core_.GetLogger(); }
  void CmdCallback(const std::shared_ptr<const my_ros2_proto::msg::JointCommand>& msg);
  void ReadSensorData(sensor_msgs::msg::Imu& imu_data, sensor_msgs::msg::JointState& joint_state);
  void WriteMotorCmd(my_ros2_proto::msg::JointCommand cmd);
  void LogGRFData();

 private:
  aimrt::CoreRef core_;
  aimrt::channel::SubscriberRef joint_cmd_sub_;
  aimrt::channel::PublisherRef imu_data_pub_;
  aimrt::channel::PublisherRef joint_state_pub_;
  std::vector<std::string> joint_names_;
  std::unordered_map<std::string, int> joint_state_index_map_;
  aimrt::executor::ExecutorRef render_executor_;
  std::atomic<bool> is_render_thread_running_ = false;

  // pid
  array_t target_q_;
  array_t target_dq_;
  array_t target_tq_;
  array_t kp_;
  array_t kd_;
  array_t motor_torque_;

  // model and data
  mjModel* m_ = nullptr;
  mjData* d_ = nullptr;
  mjtNum* ctrl_noise_ = nullptr;
  std::shared_ptr<mj::Simulate> sim_;
  std::string filename_;
  mjvCamera cam_;
  mjvOption opt_;
  mjvPerturb pert_;

  time_point<high_resolution_clock> start_time_;

  // GRF logging
  aimrt::channel::SubscriberRef walk_mode_sub_;
  std::atomic<bool> grf_walk_entered_{false};
  bool grf_logging_enabled_{false};  // [开关] true=启用, false=禁用
  bool grf_logging_triggered_{false};
  std::ofstream grf_file_;
  int grf_log_count_{0};
  int grf_log_max_count_{20 * 1000};  // 20s @ 1000Hz
  std::string grf_log_dir_;
  int floor_geom_id_{-1};
  std::set<int> left_foot_geoms_;
  std::set<int> right_foot_geoms_;
};

}  // namespace xyber_x1_infer::sim_module
