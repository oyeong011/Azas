#!/usr/bin/env bash
set -euo pipefail

echo "[Azas] actions:"
ros2 action list -t | grep -E "execute|move|trajectory" || true

echo
echo "[Azas] services:"
ros2 service list -t | grep -E "rg2|gripper|plan" || true

echo
echo "[Azas] camera topics:"
ros2 topic list | grep camera || true

echo
echo "[Azas] expected minimum:"
echo "  /execute_trajectory [moveit_msgs/action/ExecuteTrajectory]"
echo "  /jarvis/rg2/open [std_srvs/srv/Trigger]"
echo "  /jarvis/rg2/close [std_srvs/srv/Trigger]"
echo "  /plan_kinematic_path [moveit_msgs/srv/GetMotionPlan]"
echo "  /camera/camera/color/image_raw"
echo "  /camera/camera/aligned_depth_to_color/image_raw"
echo "  /camera/camera/color/camera_info"
