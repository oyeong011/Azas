# Current Handoff 2026-05-11

Purpose: durable resume point for the Azas open-source robot-control buildout.

## Objective

Find and apply open-source components until the cocktail robot can reach a robot-control-ready state.

## Current Verdict

Not complete for real hardware.

Safety state: connecting the robot does not move it. The safe dry-run entrypoint
uses `enable_hardware:=false`; real motion is only reachable through
`tools/run_robot_real.sh` after a fresh strict live-gate stamp and the typed
confirmation `ENABLE_REAL_ROBOT_MOTION`.

Completed:

- Open-source stack selected and documented.
- Doosan/MoveIt/RealSense/YOLO/STT candidates mapped to Azas roles.
- DSR_DeepTree project demo reviewed and pinned.
- DSR stepwise execution pattern applied as a no-motion cocktail task sequence.
- Non-hardware control path passes.
- Fake hardware-armed service path passes.
- Field no-motion and recovery entrypoints are available.
- Doosan real no-motion bringup entrypoint is available:
  `tools/run_doosan_real_no_motion_m0609.sh`.
- Connected no-motion field path is available:
  `tools/run_connected_robot_control.sh`.
- Strict completion audit is available and currently fails for the real-hardware blockers below.
- Camera dry-run was started once with `ENABLE_RG2=false`; YOLO/pose bridge produced live tumbler poses, then the dry-run launch was stopped.
- ROS CLI checks now accept `ROS2_DAEMON_FLAG=""` if `--no-daemon` discovery is unreliable in the field shell.
- Full cocktail no-motion workflow planning is wired: recipe plus fresh cup/lid detections now produce a gated plan covering calibration, camera-to-base pose conversion, cup pick, per-dispenser alignment/press, lid placement, cup shake, lid open, and pour.

Still blocking real robot motion:

- Real Doosan `MoveLine`/`MoveJoint` services are not confirmed in the current field state.
- Real RG2 open/close `Trigger` services are not confirmed.
- Cup/tumbler-body detection stability has not been captured after the lid test.
- Hand-eye/base-camera transform is not measured.
- `calibration.yaml` and `safety.yaml` still contain placeholder values.
- Strict live gate has not written `/tmp/azas_live_hardware_gates_passed`.

## Key Files

- `docs/recovery_after_poweroff.md`
- `docs/field_execution_commands.md`
- `docs/control_readiness_audit.md`
- `docs/field_control_runbook.md`
- `docs/real_motion_measurement_worksheet.md`
- `docs/dsr_deeptree_integration.md`
- `docs/full_cocktail_workflow_plan.md`
- `tools/recovery_after_poweroff.sh`
- `tools/verify_control_readiness.sh`
- `tools/field_no_motion_report.sh`
- `tools/robot_connection_acceptance.sh`
- `tools/real_motion_measurement_report.sh`
- `tools/check_live_hardware_gates.sh`
- `tools/completion_audit.sh`

## Reboot Resume

Run:

```bash
/home/ssu/Azas/tools/recovery_after_poweroff.sh
/home/ssu/Azas/tools/verify_control_readiness.sh
/home/ssu/Azas/tools/field_no_motion_report.sh
```

Run the strict completion audit:

```bash
/home/ssu/Azas/tools/completion_audit.sh
```

This audit is expected to fail until real-hardware evidence is complete. Latest
expected failure: `missing=8` at `2026-05-11T15:24:10+09:00`.

If Azas packages are not visible after reboot:

```bash
source /opt/ros/humble/setup.bash
cd /home/ssu/Azas
colcon build --symlink-install
source install/setup.bash
```

If Jarvis is not visible:

```bash
source /opt/ros/humble/setup.bash
cd /home/ssu/ros2_ws
colcon build --packages-select jarvis --symlink-install
source install/setup.bash
```

## Camera Resume

Plug in RealSense, then run:

```bash
ENABLE_RG2=false /home/ssu/Azas/tools/run_robot_dryrun.sh
```

In another terminal:

```bash
/home/ssu/Azas/tools/check_connection_stage.sh
/home/ssu/Azas/tools/check_depth_projection_sample.sh
/home/ssu/Azas/tools/check_robot_detection.sh
```

If those topic checks hit FastDDS/participant errors even though launch logs show
publishing, retry with ROS daemon discovery:

```bash
ROS2_DAEMON_FLAG="" /home/ssu/Azas/tools/check_connection_stage.sh
ROS2_DAEMON_FLAG="" /home/ssu/Azas/tools/check_robot_detection.sh
```

For the actual cup/tumbler body and lid:

```bash
/home/ssu/Azas/tools/check_cup_lid_sequence.sh
```

## Robot/RG2 Resume

Connected no-motion field path:

```bash
ROBOT_HOST=<robot-ip> RG2_IP=<rg2-ip> /home/ssu/Azas/tools/run_connected_robot_control.sh
```

This wrapper now stops after connected no-motion acceptance by default. Real
motion still requires `tools/run_robot_real.sh`, or an explicit supervised
`RUN_REAL_AFTER_ACCEPTANCE=true` handoff.

After Doosan is connected, start the real-controller bringup without Azas
motion/RG2 commands:

```bash
ROBOT_HOST=<robot-ip> DOOSAN_NO_MOTION_CONFIRM=CONNECT_DOOSAN_NO_MOTION /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh
```

If the Doosan stack uses a namespace:

```bash
ROBOT_NAME=dsr01 ROBOT_HOST=<robot-ip> DOOSAN_NO_MOTION_CONFIRM=CONNECT_DOOSAN_NO_MOTION /home/ssu/Azas/tools/run_doosan_real_no_motion_m0609.sh
```

After Doosan and RG2 services are running, still no motion:

```bash
STRICT_LIVE_GATE=true RUN_LID_STABILITY=true RUN_CUP_STABILITY=true /home/ssu/Azas/tools/field_no_motion_report.sh
```

Or use the one-command post-connection acceptance wrapper:

```bash
/home/ssu/Azas/tools/robot_connection_acceptance.sh
```

The strict report must pass and write:

```text
/tmp/azas_live_hardware_gates_passed
```

Only then use:

```bash
/home/ssu/Azas/tools/run_robot_real.sh
```

Expected time after hardware is connected:

- If camera, Doosan services, RG2 services, and TF are already configured: about 10-20 minutes to run the no-motion checks.
- If Doosan/RG2 service names or base-to-camera TF are missing: stop at the gate and fix those before any motion attempt.

## Last Verified Non-Hardware Evidence

`tools/verify_control_readiness.sh` passed after adding:

- cocktail dry-run sequence smoke,
- full cocktail workflow plan gate,
- fake hardware-armed smoke,
- service type contract checks,
- real-motion entrypoint fail-closed smoke,
- real-motion config gate smoke,
- field no-motion and recovery scripts syntax checks.

Latest local verifier run:

- `tools/verify_control_readiness.sh` passed at `2026-05-12T12:56:22+09:00`.
- This proves the offline plan and fail-closed gates are wired; it still does
  not prove live camera detection, measured hand-eye calibration, real RG2
  behavior, or real Doosan motion.

Warnings that are acceptable for now:

- `lang_sam`, `vosk`, and `whisper` optional imports are missing.

Latest completion audit:

- `tools/completion_audit.sh` was run at `2026-05-11T15:53:13+09:00`.
- Verdict remains `NOT COMPLETE`, `missing=8`.
- Verified: non-hardware stack, fake hardware-armed path, cocktail dry-run sequence, Doosan virtual/real no-motion launch argument resolution, command sheet, connected robot-control wrapper, and real-motion fail-closed gates.
- Missing: fresh strict live gate stamp, measured production calibration/safety config, cup/tumbler-body stability PASS, lid stability PASS, live hardware gate PASS, hand-eye/base-camera TF readiness PASS, RG2 actuation marked done, and real robot hardware gate marked done.
- Current operator instruction: do not run Doosan real bringup until the physical robot is connected and the user says to execute.

Latest network evidence:

- Host wired interface: `enp128s31f6`.
- Active host IP observed: `203.246.36.217/24`.
- `ping 192.168.137.100` failed.
- `ping 192.168.127.100` failed.
- `ip neigh` did not show those Doosan defaults; it did show unrelated
  `192.168.37.15` and `192.168.37.17` neighbors on the wire.
- Attempting to add `192.168.137.50/24` as a secondary address requires sudo
  password, so the operator must run:
  `sudo ip addr add 192.168.137.50/24 dev enp128s31f6`.

## 2026-05-12 Resume Note

- Stale ROS processes from 2026-05-11 were found and stopped: duplicate Doosan
  launch/emulator/controller/move_group nodes plus stale RealSense, YOLO, static
  TF, RG2, and tumbler floor-place nodes.
- No Doosan motion service call and no RG2 trigger call was sent during cleanup.
- After cleanup, `check_connection_stage.sh` and `check_live_hardware_gates.sh`
  correctly report missing camera topics, Doosan MoveLine/MoveJoint services,
  and RG2 open/close services.
- `lsusb` currently does not show the Intel RealSense device.
- `enp128s31f6` still has only `203.246.36.217/24`; `ping 192.168.137.100` and
  `ping 192.168.127.100` still fail.
- `/tmp/azas_motion_hold` remains active with reason `glass in robot workspace;
  user requested no robot motion`.

Current next step: physically connect the RealSense first, rerun
`ENABLE_RG2=false /home/ssu/Azas/tools/run_robot_dryrun.sh`, then rerun
`/home/ssu/Azas/tools/check_robot_detection.sh` and
`/home/ssu/Azas/tools/check_depth_projection_sample.sh`. Do not attempt real
robot motion until the robot subnet, strict live gate, measured config, and
motion hold are all resolved.

## Do Not Do

- Do not fill `calibration.yaml` or `safety.yaml` with guessed values.
- Do not bypass `run_robot_real.sh` with ad-hoc real-motion launch commands.
- Do not treat fake-hardware smoke as proof of real robot readiness.
- Do not claim the overall objective complete until `docs/control_readiness_audit.md` has no missing real-hardware items.
