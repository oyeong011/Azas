# Camera Connection Verification - 2026-05-11

Purpose: record live RealSense camera evidence before connecting the real robot/RG2.

## Result

The connected camera is recognized as an Intel RealSense D435i. ROS dry-run bringup starts the RealSense node, publishes color/depth/CameraInfo topics, and depth projection passes. YOLO/perception topics are present. After placing the object in view, the model produced stable fresh `detected:lid` samples with valid depth.

## Hardware Evidence

`lsusb`:

```text
Bus 004 Device 002: ID 8086:0b3a Intel Corp. Intel(R) RealSense(TM) Depth Camera 435i
```

`v4l2-ctl --list-devices`:

```text
Intel(R) RealSense(TM) Depth Ca (usb-0000:80:14.0-7):
  /dev/video0
  /dev/video1
  /dev/video2
  /dev/video3
  /dev/video4
  /dev/video5
  /dev/media0
  /dev/media1
```

## Dry-Run Bringup

Command:

```bash
ENABLE_RG2=false /home/ssu/Azas/tools/run_robot_dryrun.sh
```

Observed RealSense startup:

```text
RealSense ROS v4.57.7
Built with LibRealSense v2.57.7
Device with name Intel RealSense D435I was found.
Device USB type: 3.2
RealSense Node Is Up!
```

## ROS Topic Evidence

Camera/perception topics:

```text
/azas/cup_detection
/camera/aligned_depth_to_color/camera_info
/camera/aligned_depth_to_color/image_raw
/camera/color/camera_info
/camera/color/image_raw
/camera/depth/camera_info
/camera/depth/image_rect_raw
/jarvis/tumbler_dispenser/tumbler_pose
/jarvis/tumbler_floor_place/plan
/jarvis/tumbler_floor_place/status
```

CameraInfo sample:

```text
frame_id: camera_color_optical_frame
height: 720
width: 1280
k: [910.474365234375, 0.0, 638.866943359375, 0.0, 910.2800903320312, 351.2701721191406, 0.0, 0.0, 1.0]
```

Depth projection:

```text
[PASS] depth projection sample frame='camera_color_optical_frame' pixel=(640,360) depth_raw=310.000 point_camera_m=(0.0004,0.0030,0.3100)
```

## Detection Status

YOLO model classes:

```text
{0: 'cup', 1: 'lid'}
```

Initial samples before placing the object correctly showed:

```text
status: no_tumbler_detection
status: invalid_depth_at_detection
confidence: 0.0
source: yolo_tumbler_detector
```

After placing the object in camera view, repeated `/azas/cup_detection` samples showed stable lid classification:

```text
frame_id: camera_color_optical_frame
confidence: 0.9722573161125183
status: detected:lid bbox=299x278 depth_raw=264.0
source: yolo_tumbler_detector

frame_id: camera_color_optical_frame
confidence: 0.9736297726631165
status: detected:lid bbox=299x277 depth_raw=264.0
source: yolo_tumbler_detector
```

The no-motion stage report also showed:

```text
cup detection sample  OK detected:lid bbox=300x278 depth_raw=264.0 confidence=0.9726579785346985
```

Pose bridge output:

```text
frame_id: camera_color_optical_frame
pose.position: x=-0.014749314818345413 y=-0.025020129168315284 z=0.264
```

## Boundary

Do not connect the real robot for motion based on this evidence alone. The camera and lid detection stage is verified, but the next vision check is to place the cup/tumbler body clearly in view and confirm `detected:cup`.

```bash
/home/ssu/Azas/tools/check_robot_detection.sh
/home/ssu/Azas/tools/check_connection_stage.sh
```

Keep the object in the color camera center, avoid reflective/edge-only depth regions, and keep it within the RealSense depth range. Real motion remains blocked until Doosan/RG2 no-motion service checks, hand-eye/base-frame calibration, measured safety config, and strict live gates pass.
