# RViz Simulation Verification - 2026-05-11

Purpose: verify what can be run before the camera and robot are connected.

## Result

RViz-only tumbler/dispenser simulation runs without connecting the real robot. The scene node publishes the expected visualization/control topics, and the floor-place dry-run controller can consume the simulated tumbler pose and reach `DONE` with hardware disabled.

## Commands

RViz scene:

```bash
source /opt/ros/humble/setup.bash
source /home/ssu/ros2_ws/install/setup.bash
ros2 launch jarvis tumbler_dispenser_scene.launch.py selected_dispenser_id:=2 use_rviz:=true
```

Dry-run controller connected to the RViz scene pose:

```bash
source /opt/ros/humble/setup.bash
source /home/ssu/ros2_ws/install/setup.bash
ros2 launch jarvis tumbler_floor_place.launch.py \
  selected_dispenser_id:=2 \
  use_tumbler_pose_topic:=true \
  tumbler_pose_topic:=/jarvis/tumbler_dispenser/tumbler_pose \
  enable_hardware:=false \
  allow_demo_tumbler_position_fallback:=false
```

## Evidence

Published RViz scene topics:

```text
/jarvis/tumbler_dispenser/markers
/jarvis/tumbler_dispenser/outlet_pose
/jarvis/tumbler_dispenser/target_pose
/jarvis/tumbler_dispenser/transfer_path
/jarvis/tumbler_dispenser/tumbler_pose
/tf
/tf_static
```

Selected dispenser 2 target pose:

```text
frame_id: base_link
position: x=0.435 y=0.05 z=0.0
orientation: x=0.0 y=0.0 z=0.0 w=1.0
```

Simulated tumbler pose:

```text
frame_id: base_link
position: x=0.32 y=-0.22 z=0.05
orientation: x=0.0 y=0.08987854919801104 z=0.0 w=0.9959527330119943
```

Transfer path publishes waypoints from side approach/side grasp/slight-lift through a front clear lane to the selected outlet target. The controller now generates robot-side radial, detected-yaw, and 16 circular side-grasp candidates, then chooses the first candidate that passes workspace and dispenser keep-out checks. Key points:

```text
side_pre_grasp x=0.238 y=-0.163 z=0.135
side_grasp/lift at x=0.32 y=-0.22
selected d2 fixed place x=0.580 y=-0.065 z=0.0
```

RViz scene feasibility log:

```text
M0609/RG2 feasibility: OK
RViz-only four-dispenser array: selected 2/4; hardware disabled
reach pick=OK 0.400/0.900 m
reach target=OK 0.438/0.900 m
RG2 stroke=OK 0.075/0.110 m
payload force-fit=OK 0.35/2.00 kg
payload M0609=OK 0.35/6.00 kg
```

Floor-place dry-run controller log:

```text
Using detected tumbler pose: x=0.320 y=-0.220 z=0.050
Gripper taper targets: diameter_at_grasp=0.070 preopen_width=0.095 grasp_width=0.064
plan side_pre_grasp: x=0.238 y=-0.163 z=0.135 gripper=preopen width_m=0.095 force_n=8.0
plan side_grasp_tumbler: x=0.320 y=-0.220 z=0.135 gripper=close width_m=0.064 force_n=12.0
plan lift_tumbler: x=0.320 y=-0.220 z=0.175 gripper=none
plan pre_floor_place: x=0.580 y=-0.065 z=0.145 gripper=none
plan floor_place: x=0.580 y=-0.065 z=0.085 gripper=open
plan retreat_after_place: x=0.580 y=-0.065 z=0.145 gripper=none
Hardware not armed. Dry-run only.
DONE
```

## Boundary

This verifies RViz scene visualization and dry-run control-path execution only. It does not verify:

- live RealSense image/depth topics,
- YOLO detection on the actual tumbler/lid,
- camera depth projection with a known-distance target,
- camera-to-base or hand-eye calibration,
- MoveIt planning against measured poses,
- real RG2 actuation,
- real Doosan motion.

Next recommended physical step: connect the camera only, then run the camera checks in `docs/simulation_and_connection_plan.md`.
