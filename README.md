# Azas

ROS2 package for a Doosan robot dispenser press task.

The package contains the Jarvis dispenser motion node. It moves the robot to HOME, uses the current TCP pose as the dispenser approach pose, moves down 30 mm, presses 15 mm, holds for 0.5 seconds, retreats, and returns HOME.

## Dependencies

This repository only contains the custom task package. It must be built in a ROS2 workspace that also contains the required Doosan ROS2 packages.

Required packages:

- `dsr_msgs2`
- `dsr_controller2`
- `dsr_hardware2`
- `dsr_common2`
- `dsr_bringup2`
- `dsr_description2`

Optional for Gazebo:

- `dsr_gazebo2`

## Workspace Setup

Create a workspace and clone the Doosan packages plus this package:

```bash
mkdir -p ~/jarvis_ws/src
cd ~/jarvis_ws/src

# Clone or copy doosan-robot2 here first.
# Then clone this package:
git clone https://github.com/ROS2JARVIS/Azas.git jarvis
```

Build:

```bash
cd ~/jarvis_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

## Run With Virtual Robot

Terminal 1:

```bash
source /opt/ros/humble/setup.bash
source ~/jarvis_ws/install/setup.bash
ros2 launch dsr_bringup2 dsr_bringup2_moveit.launch.py mode:=virtual model:=m0609
```

Terminal 2:

```bash
source /opt/ros/humble/setup.bash
source ~/jarvis_ws/install/setup.bash
ros2 launch jarvis dispenser_press.launch.py
```

## Parameters

Main parameters are in `launch/dispenser_press.launch.py`.

- `use_home_as_reference`: If true, HOME/current TCP pose is used as the approach pose.
- `approach_height`: Distance from approach pose to dispenser top, in meters. Default `0.03`.
- `press_depth`: Press distance below dispenser top, in meters. Default `0.015`.
- `hold_seconds`: Time to hold the press. Default `0.5`.
- `service_prefix`: Set this if Doosan services are namespaced, for example `dsr01`.

If `use_home_as_reference` is true, the node does not use fixed dispenser `x`, `y`, `z` values. It reads the current TCP pose after HOME and moves only along the base Z axis.

