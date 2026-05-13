#!/usr/bin/env bash
set -euo pipefail

SESSION="${SESSION:-azas_cup_pick}"
AZAS_DIR="${AZAS_DIR:-$HOME/Azas}"
ROS_WS="${ROS_WS:-$HOME/ros2_ws}"
ROBOT_HOST="${ROBOT_HOST:-192.168.1.100}"
MODEL="${MODEL:-m0609}"

tmux has-session -t "${SESSION}" 2>/dev/null && {
  echo "[Azas] tmux session already exists: ${SESSION}"
  echo "Attach: tmux attach -t ${SESSION}"
  exit 0
}

tmux new-session -d -s "${SESSION}" -n bringup

# Pane 0: Doosan MoveIt real
tmux send-keys -t "${SESSION}:0.0" "cd ${AZAS_DIR}" C-m
tmux send-keys -t "${SESSION}:0.0" "source /opt/ros/humble/setup.bash && source ${ROS_WS}/install/setup.bash && source ${AZAS_DIR}/install/setup.bash" C-m
tmux send-keys -t "${SESSION}:0.0" "ros2 launch dsr_bringup2 dsr_bringup2_moveit.launch.py model:=${MODEL} mode:=real host:=${ROBOT_HOST}" C-m

# Pane 1: RG2
tmux split-window -h -t "${SESSION}:0"
tmux send-keys -t "${SESSION}:0.1" "cd ${AZAS_DIR}" C-m
tmux send-keys -t "${SESSION}:0.1" "source /opt/ros/humble/setup.bash && source ${ROS_WS}/install/setup.bash && source ${AZAS_DIR}/install/setup.bash" C-m
tmux send-keys -t "${SESSION}:0.1" "ros2 launch jarvis rg2_trigger.launch.py ip:=192.168.1.1 open_width:=500 close_width:=200 force:=200 settle_seconds:=1.0" C-m

# Pane 2: RealSense
tmux split-window -v -t "${SESSION}:0.0"
tmux send-keys -t "${SESSION}:0.2" "cd ${AZAS_DIR}" C-m
tmux send-keys -t "${SESSION}:0.2" "source /opt/ros/humble/setup.bash && source ${AZAS_DIR}/install/setup.bash" C-m
tmux send-keys -t "${SESSION}:0.2" "ros2 launch realsense2_camera rs_align_depth_launch.py depth_module.depth_profile:=640x480x30 rgb_camera.color_profile:=640x480x30 initial_reset:=true align_depth.enable:=true" C-m

# Pane 3: checks
tmux split-window -v -t "${SESSION}:0.1"
tmux send-keys -t "${SESSION}:0.3" "cd ${AZAS_DIR}" C-m
tmux send-keys -t "${SESSION}:0.3" "source /opt/ros/humble/setup.bash && source ${ROS_WS}/install/setup.bash && source ${AZAS_DIR}/install/setup.bash" C-m
tmux send-keys -t "${SESSION}:0.3" "echo '[Azas] Wait 15 sec, then run: bash tools/check_cup_pick_backends.sh'" C-m

# New window: command shell
tmux new-window -t "${SESSION}" -n pick
tmux send-keys -t "${SESSION}:1.0" "cd ${AZAS_DIR}" C-m
tmux send-keys -t "${SESSION}:1.0" "source /opt/ros/humble/setup.bash && source ${ROS_WS}/install/setup.bash && source ${AZAS_DIR}/install/setup.bash" C-m
tmux send-keys -t "${SESSION}:1.0" "echo '[Azas] Commands:'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo '1) observe only:'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo 'python3 tools/run_supervised_real_single_cup_pick.py --enable-real-motion --confirm I_UNDERSTAND_THIS_WILL_MOVE_THE_ROBOT --one-shot --observe-only'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo '2) export frame:'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo 'python3 tools/export_grasp_frame.py --output /tmp/azas_grasp_frame --rgb-topic /camera/camera/color/image_raw --depth-topic /camera/camera/aligned_depth_to_color/image_raw --camera-info-topic /camera/camera/color/camera_info --timeout-sec 10'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo '3) dry-run manual pose:'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo 'python3 tools/run_supervised_real_single_cup_pick.py --dry-run --skip-observe --cup-reference-x 0.42 --cup-reference-y -0.24 --cup-reference-z 0.05'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo '4) real one-shot manual pose:'" C-m
tmux send-keys -t "${SESSION}:1.0" "echo 'python3 tools/run_supervised_real_single_cup_pick.py --enable-real-motion --confirm I_UNDERSTAND_THIS_WILL_MOVE_THE_ROBOT --one-shot --skip-observe --cup-reference-x 0.42 --cup-reference-y -0.24 --cup-reference-z 0.05'" C-m

tmux select-window -t "${SESSION}:0"
tmux attach -t "${SESSION}"
