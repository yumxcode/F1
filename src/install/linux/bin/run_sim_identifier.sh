#!/bin/bash

# source ROS2 环境（conda ros_humble）
if [ -f /home/robot/Anaconda/envs/F1/ros_humble/setup.bash ]; then
    source /home/robot/Anaconda/envs/F1/ros_humble/setup.bash
fi

if [ -f ./install/share/ros2_plugin_proto/local_setup.bash ]; then
    source ./install/share/ros2_plugin_proto/local_setup.bash
elif [ -f ../share/ros2_plugin_proto/local_setup.bash ]; then
    source ../share/ros2_plugin_proto/local_setup.bash
fi

if [ -f ./install/share/my_ros2_proto/local_setup.bash ]; then
    source ./install/share/my_ros2_proto/local_setup.bash
elif [ -f ../share/my_ros2_proto/local_setup.bash ]; then
    source ../share/my_ros2_proto/local_setup.bash
fi

# 将 ROS2 lib 和 install/lib 加入 LD_LIBRARY_PATH
export LD_LIBRARY_PATH="/home/robot/Anaconda/envs/F1/ros_humble/lib:$(dirname "$0")/install/lib:${LD_LIBRARY_PATH}"

./aimrt_main --cfg_file_path=./cfg/x1_cfg_sim_identifier.yaml
