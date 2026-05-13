#!/usr/bin/env bash
set -euo pipefail

# Multi-position dry-run smoke for side-grasp candidate selection.
# It sends no hardware commands; it verifies that arbitrary cup centers inside
# the configured workspace produce a valid side_pre_grasp and DONE status.

export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"
mkdir -p "${ROS_LOG_DIR}"

set +u
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
source /home/ssu/ros2_ws/install/setup.bash 2>/dev/null || true
set -u

cleanup_case() {
  if [[ -n "${LAUNCH_PID:-}" ]] && kill -0 "${LAUNCH_PID}" 2>/dev/null; then
    kill "${LAUNCH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${STATUS_PID:-}" ]] && kill -0 "${STATUS_PID}" 2>/dev/null; then
    kill "${STATUS_PID}" 2>/dev/null || true
  fi
}

run_case() {
  local label="$1"
  local cup_x="$2"
  local cup_y="$3"
  local expected_pre_x="$4"
  local expected_pre_y="$5"
  local status_file="/tmp/azas_random_grasp_${label}_status.txt"
  local log_file="/tmp/azas_random_grasp_${label}.log"
  local cup_topic="/azas/random_grasp/${label}/cup_detection"
  local pose_topic="/azas/random_grasp/${label}/tumbler_pose"

  rm -f "${status_file}" "${log_file}"
  LAUNCH_PID=""
  STATUS_PID=""
  trap cleanup_case RETURN

  ros2 launch azas_bringup simulated_cup_grasp_dryrun.launch.py \
    selected_dispenser_id:=2 \
    publish_once:=false \
    cup_detection_topic:="${cup_topic}" \
    tumbler_pose_topic:="${pose_topic}" \
    grasp_x:="${cup_x}" \
    grasp_y:="${cup_y}" \
    grasp_z:=0.05 \
    mouth_x:="${cup_x}" \
    mouth_y:="${cup_y}" \
    mouth_z:=0.22 \
    >"${log_file}" 2>&1 &
  LAUNCH_PID=$!

  timeout 20s ros2 topic echo /jarvis/tumbler_floor_place/status --field data --no-daemon \
    >"${status_file}" 2>/tmp/azas_random_grasp_${label}_status.err &
  STATUS_PID=$!

  for _ in {1..40}; do
    if grep -q "DONE" "${status_file}" 2>/dev/null || grep -q "tumbler_floor_place_node.*DONE" "${log_file}" 2>/dev/null; then
      if ! grep -Eq "plan side_pre_grasp: x=${expected_pre_x} y=${expected_pre_y} z=0\\.135 gripper=preopen" "${log_file}"; then
        echo "[FAIL] ${label}: side_pre_grasp mismatch"
        sed -n '1,220p' "${log_file}"
        return 1
      fi
      if ! grep -q "Selected side grasp candidate" "${log_file}"; then
        echo "[FAIL] ${label}: candidate selection log missing"
        sed -n '1,220p' "${log_file}"
        return 1
      fi
      echo "[OK] ${label}: cup=(${cup_x},${cup_y}) pre=(${expected_pre_x},${expected_pre_y})"
      return 0
    fi
    if grep -q "FAILED" "${status_file}" 2>/dev/null || grep -q "tumbler_floor_place_node.*FAILED" "${log_file}" 2>/dev/null; then
      echo "[FAIL] ${label}: reached FAILED"
      sed -n '1,220p' "${log_file}"
      return 1
    fi
    sleep 0.5
  done

  echo "[FAIL] ${label}: did not reach DONE"
  sed -n '1,220p' "${log_file}"
  return 1
}

run_case "front_right" "0.32" "-0.22" "0\\.238" "-0\\.163"
run_case "front_left" "0.20" "0.24" "0\\.136" "0\\.163"
run_case "near_y_min" "0.08" "-0.30" "0\\.054" "-0\\.203"
run_case "near_robot" "0.07" "0.02" "0\\.170" "0\\.020"

rejected_log="/tmp/azas_random_grasp_reject_no_candidate.log"
rm -f "${rejected_log}"
LAUNCH_PID=""
trap cleanup_case RETURN
ros2 launch jarvis tumbler_floor_place.launch.py \
  selected_dispenser_id:=2 \
  use_tumbler_pose_topic:=false \
  side_grasp_candidate_count:=0 \
  tumbler_position_x:=0.01 \
  tumbler_position_y:=0.0 \
  tumbler_position_z:=0.05 \
  >"${rejected_log}" 2>&1 &
LAUNCH_PID=$!

for _ in {1..30}; do
  if grep -q "FAILED" "${rejected_log}" 2>/dev/null; then
    if grep -q "No side grasp candidate passed workspace/keep-out checks" "${rejected_log}" \
      && grep -q "no valid side grasp candidate" "${rejected_log}"; then
      echo "[OK] reject_no_candidate: planner failed closed without radial fallback"
      cleanup_case
      LAUNCH_PID=""
      break
    fi
    echo "[FAIL] reject_no_candidate: missing fail-closed evidence"
    sed -n '1,220p' "${rejected_log}"
    exit 1
  fi
  if grep -q "DONE" "${rejected_log}" 2>/dev/null; then
    echo "[FAIL] reject_no_candidate: unsafe candidate fallback reached DONE"
    sed -n '1,220p' "${rejected_log}"
    exit 1
  fi
  sleep 0.5
done

if [[ -n "${LAUNCH_PID}" ]]; then
  echo "[FAIL] reject_no_candidate: did not reach FAILED"
  sed -n '1,220p' "${rejected_log}"
  exit 1
fi

echo "[PASS] random cup side-grasp candidates reached DONE"
