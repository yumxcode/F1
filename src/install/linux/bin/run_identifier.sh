#!/bin/bash

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

export LD_LIBRARY_PATH="$(dirname "$0")/install/lib:${LD_LIBRARY_PATH}"

sudo setcap cap_net_raw=ep ./aimrt_main
./aimrt_main --cfg_file_path=./cfg/x1_cfg_identifier.yaml
