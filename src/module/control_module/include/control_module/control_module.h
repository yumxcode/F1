#pragma once

#include <chrono>
#include <memory>
#include <set>
#include <fstream>
#include <filesystem>
#include "aimrt_module_cpp_interface/module_base.h"
#include "control_module/pd_controller.h"
#include "control_module/rl_controller.h"
#include "control_module/state_machine.h"
// #include "control_module/joint_groups.h"

using namespace std::chrono;

namespace xyber_x1_infer::rl_control_module {

class ControlModule : public aimrt::ModuleBase {
 public:
  ControlModule() = default;
  ~ControlModule() override = default;
  [[nodiscard]] aimrt::ModuleInfo Info() const override {
    return aimrt::ModuleInfo{.name = "ControlModule"};
  }
  bool Initialize(aimrt::CoreRef core) override;
  bool Start() override;
  void Shutdown() override;

 private:
  bool MainLoop();

 private:
  aimrt::CoreRef core_;
  aimrt::executor::ExecutorRef executor_;

  std::vector<aimrt::channel::SubscriberRef> subs_;
  aimrt::channel::PublisherRef joint_cmd_pub_;

  StateMachine state_machine_;
  std::set<std::string> trigger_topics_;//// 添加重复的 trigger_topic 会报错，这里用 set 来存储
  std::map<std::string, std::shared_ptr<ControllerBase>> controller_map_;
  std::unordered_map<std::string, int> joint_state_index_map_;
  std::unordered_map<std::string, int> joint_cmd_index_map_;
  std::map<std::string, double> joint_offset_map_;

  bool use_sim_handles_;
  int32_t freq_;
  std::atomic_bool run_flag_{true};
  time_point<high_resolution_clock> last_trigger_time_;

  // T1-4 延迟测试 CSV 日志
  std::ofstream t14_log_file_;
  bool t14_logging_enabled_{false};
  int t14_log_count_{0};
  int t14_log_max_count_{0};
  std::atomic<int64_t> last_joint_state_recv_ns_{0};
};

}  // namespace xyber_x1_infer::rl_control_module
