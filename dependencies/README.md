# External ROS 2 Sources

Azas does **not** vendor third-party source trees into this repository. External ROS 2 packages are tracked as `vcs` manifests so their upstream history, license files, and review boundaries remain explicit.

## Why `.repos` instead of vendoring

- Keeps Azas diffs focused on project code, wiki decisions, and integration glue.
- Avoids accidentally committing large upstream source trees.
- Preserves upstream license and commit provenance.
- Allows review workspaces under `/tmp` before any dependency is accepted into the main ROS workspace.
- Supports the project rule that robot coordinates must come from calibrated vision/config data, not LLM/VLA outputs or opaque imported behavior.

## Review import commands

Run imports only in a disposable review workspace first:

```bash
mkdir -p /tmp/azas_oss_review/src
cd /tmp/azas_oss_review
vcs import src < /home/ssu/Azas/dependencies/ros2_sources.repos
rosdep install -r --from-paths src --ignore-src --rosdistro humble -y
colcon build --symlink-install
```

Experimental/high-risk sources are separated:

```bash
mkdir -p /tmp/azas_oss_review_experimental/src
cd /tmp/azas_oss_review_experimental
vcs import src < /home/ssu/Azas/dependencies/experimental_sources.repos
```

Do not copy imported `src/external/*` or `src/experimental/*` trees back into `/home/ssu/Azas`.

Project demo code is tracked separately so it can be reviewed without vendoring:

```bash
mkdir -p /tmp/azas_demo_review/src
cd /tmp/azas_demo_review
vcs import src < /home/ssu/Azas/dependencies/dsr_deeptree_sources.repos
```

Current demo source: `deeptree0819/DSR_DeepTree` pinned at commit `22f5435086037a759e563047f535f2c3c418351e`.

Optional Python runtime dependencies are kept separate from ROS source manifests:

```bash
python3 -m pip install -r /home/ssu/Azas/dependencies/python_optional_requirements.txt
```

System package candidates are listed in `system_apt_packages.txt`. Review the target Ubuntu/ROS image before installing them on the robot PC.

## Review order

1. **Doosan ROS 2**: verify Humble branch, M0609 model string, virtual emulator, `dsr_bringup2` MoveIt launch, and license files.
2. **MoveIt 2 / MoveItPy**: prefer binary packages for normal development; source import is for API/config review and gap debugging.
3. **RealSense ROS 2 wrapper**: verify camera model, stream profiles, topic names, `CameraInfo`, depth scale, and frame IDs.
4. **AprilTag ROS 2**: verify `image_rect`/`camera_info` remaps and marker TF naming for calibration target.
5. **easy_handeye2**: verify Humble build and freehand sampling workflow before using its TF publisher.
6. **OnRobot ROS2 Driver**: experimental only; test fake hardware first, then document Modbus connection, speed/force limits, stop behavior, and failure handling before any hardware trial.
7. **AnyGrasp ROS 2**: experimental only; review SDK license registration, ROS distro mismatch, CUDA/PyTorch container requirements, service contracts, and frame conventions before connecting to `PickAndAlign`.
8. **DSR_DeepTree demo**: review Task 1 action sequencing, Task 2 YOLO/hand-eye conversion, Task 3 STT command mapping, and Task 4 Isaac Sim assets. Port patterns only; do not vendor the full tree.

## Safety gate

Any dependency that can affect hardware motion must have an Azas integration note documenting:

- safety assumptions and operator controls,
- speed/acceleration/force limits,
- expected failure behavior,
- verification steps in virtual/fake hardware mode,
- criteria for moving to real hardware.

## Non-hardware stack check

After building Azas and the local `ros2_ws` bridge packages, run:

```bash
/home/ssu/Azas/tools/check_oss_stack.sh
```

This checks ROS package availability, key launch descriptions, optional Python imports, and the expected local YOLO model path without starting cameras, RG2, or real robot motion.
