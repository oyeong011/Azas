#!/usr/bin/env bash
set -euo pipefail

# Reproducible non-hardware verifier for the Azas open-source robot-control stack.
# It builds/tests nothing destructive and sends no motion or gripper commands.

REPORT="${REPORT:-/tmp/azas_control_readiness_report.txt}"
STRICT_OPTIONAL="${STRICT_OPTIONAL:-false}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/azas_ros_logs}"

rm -f "${REPORT}"
mkdir -p "${ROS_LOG_DIR}"

section() {
  local title="$1"
  {
    echo
    echo "## ${title}"
  } | tee -a "${REPORT}"
}

run_step() {
  local label="$1"
  shift
  section "${label}"
  if "$@" 2>&1 | tee -a "${REPORT}"; then
    echo "[RESULT] ${label}: PASS" | tee -a "${REPORT}"
  else
    echo "[RESULT] ${label}: FAIL" | tee -a "${REPORT}"
    return 1
  fi
}

{
  echo "# Azas Control Readiness Report"
  date -Is
  echo
  echo "Scope: non-hardware verifier. No robot motion or gripper commands are sent."
  echo "Strict optional dependencies: ${STRICT_OPTIONAL}"
} | tee -a "${REPORT}"

run_step "Script syntax" bash -lc '
  bash -n /home/ssu/Azas/tools/check_oss_stack.sh
  bash -n /home/ssu/Azas/tools/smoke_control_path.sh
  bash -n /home/ssu/Azas/tools/check_live_hardware_gates.sh
  bash -n /home/ssu/Azas/tools/check_connection_stage.sh
  bash -n /home/ssu/Azas/tools/check_real_motion_config.sh
  bash -n /home/ssu/Azas/tools/explain_real_robot_blockers.sh
  bash -n /home/ssu/Azas/tools/run_doosan_virtual_m0609.sh
  bash -n /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh
  bash -n /home/ssu/Azas/tools/run_connected_robot_control.sh
  bash -n /home/ssu/Azas/tools/run_robot_dryrun.sh
  bash -n /home/ssu/Azas/tools/run_robot_real.sh
  bash -n /home/ssu/Azas/tools/smoke_fake_hardware_path.sh
	  bash -n /home/ssu/Azas/tools/smoke_random_cup_grasp_candidates.sh
	  bash -n /home/ssu/Azas/tools/smoke_stage_execution_modes.sh
	  bash -n /home/ssu/Azas/tools/smoke_dispense_lid_sequence.sh
	  bash -n /home/ssu/Azas/tools/smoke_tumbler_shake_sequence.sh
  bash -n /home/ssu/Azas/tools/check_depth_projection_sample.sh
  bash -n /home/ssu/Azas/tools/check_detection_stability.sh
  bash -n /home/ssu/Azas/tools/smoke_cocktail_dryrun_sequence.sh
  bash -n /home/ssu/Azas/tools/field_no_motion_report.sh
  bash -n /home/ssu/Azas/tools/robot_connection_acceptance.sh
  bash -n /home/ssu/Azas/tools/smoke_robot_connection_acceptance_gate.sh
  bash -n /home/ssu/Azas/tools/real_motion_measurement_report.sh
  bash -n /home/ssu/Azas/tools/smoke_real_motion_entrypoint_gates.sh
  bash -n /home/ssu/Azas/tools/smoke_real_motion_config_gate.sh
  bash -n /home/ssu/Azas/tools/completion_audit.sh
  python3 -m py_compile /home/ssu/Azas/tools/fake_hardware_services.py
  python3 -m py_compile /home/ssu/Azas/tools/check_static_cup_lid_dataset.py
  python3 -m py_compile /home/ssu/Azas/tools/check_fixed_dispenser_geometry.py
  python3 -m py_compile /home/ssu/Azas/tools/check_cocktail_workflow_plan.py
  python3 -m py_compile /home/ssu/Azas/tools/check_depth_projection_sample.py
  python3 -m py_compile /home/ssu/Azas/tools/check_detection_stability.py
  python3 -m py_compile /home/ssu/Azas/tools/smoke_cocktail_dryrun_sequence.py
  python3 -m py_compile /home/ssu/Azas/src/azas_task_manager/azas_task_manager/cocktail_workflow_plan.py
  python3 -m py_compile /home/ssu/Azas/src/azas_task_manager/azas_task_manager/cocktail_dryrun_sequence_node.py
'

run_step "OSS stack availability" env STRICT_OPTIONAL="${STRICT_OPTIONAL}" /home/ssu/Azas/tools/check_oss_stack.sh

run_step "Static cup/lid photo dataset gate" /home/ssu/Azas/tools/check_static_cup_lid_dataset.py

run_step "Fixed dispenser geometry gate" /home/ssu/Azas/tools/check_fixed_dispenser_geometry.py

run_step "Non-hardware control smoke" /home/ssu/Azas/tools/smoke_control_path.sh

run_step "Fake hardware-armed smoke" /home/ssu/Azas/tools/smoke_fake_hardware_path.sh

run_step "Random cup side-grasp candidate smoke" /home/ssu/Azas/tools/smoke_random_cup_grasp_candidates.sh

run_step "Stage execution mode smoke" /home/ssu/Azas/tools/smoke_stage_execution_modes.sh

run_step "Dispenser press and lid-close fake hardware smoke" /home/ssu/Azas/tools/smoke_dispense_lid_sequence.sh

run_step "Safe-space tumbler shake fake hardware smoke" /home/ssu/Azas/tools/smoke_tumbler_shake_sequence.sh

run_step "Cocktail dry-run sequence smoke" /home/ssu/Azas/tools/smoke_cocktail_dryrun_sequence.sh

run_step "Full cocktail workflow plan gate" /home/ssu/Azas/tools/check_cocktail_workflow_plan.py

run_step "Real-motion entrypoint fail-closed smoke" /home/ssu/Azas/tools/smoke_real_motion_entrypoint_gates.sh

run_step "Robot connection acceptance fail-closed smoke" /home/ssu/Azas/tools/smoke_robot_connection_acceptance_gate.sh

run_step "Real-motion config gate smoke" /home/ssu/Azas/tools/smoke_real_motion_config_gate.sh

run_step "Doosan virtual launch args" bash -lc '
  source /opt/ros/humble/setup.bash
  source /home/ssu/ros2_ws/install/setup.bash
  timeout 20s ros2 launch dsr_bringup2 dsr_bringup2_moveit.launch.py --show-args
'

run_step "Doosan real no-motion launch args" env SHOW_ARGS_ONLY=true /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh

{
  echo
  echo "## Completion Boundary"
  echo "PASS here means the local non-hardware stack is wired."
  echo "It does not prove real camera detection, hand-eye calibration, RG2 actuation, MoveIt feasibility for measured poses, e-stop behavior, or real Doosan motion."
  echo "Run /home/ssu/Azas/tools/check_live_hardware_gates.sh after live bringup for field evidence."
  echo
  echo "Report: ${REPORT}"
} | tee -a "${REPORT}"
