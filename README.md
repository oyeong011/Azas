# Azas

ROS2 기반 JARVIS 작업 패키지입니다.

이 저장소는 Doosan ROS2 환경 위에서 팀원들이 각자 기능 노드를 추가해 나가기 위한 초기 패키지입니다. 현재는 최소 실행 구조와 예시 launch/node 구성이 포함되어 있으며, 이후 기능별 Python node와 launch 파일을 확장해 사용합니다.

## 목적

- 팀 공용 ROS2 Python 패키지 제공
- 기능별 node를 한 패키지 안에서 관리
- Doosan ROS2 패키지는 외부 의존성으로 두고, 팀 코드만 이 저장소에서 관리
- 공동작업자가 동일한 방식으로 build, source, launch 할 수 있도록 기본 구조 제공

## 필요 환경

- Ubuntu 22.04
- ROS2 Humble
- `colcon`
- Doosan ROS2 패키지

이 저장소는 Doosan 전체 패키지를 포함하지 않습니다. 아래 패키지들이 같은 workspace에 있거나, 이미 ROS 환경에 source 되어 있어야 합니다.

필수 의존 패키지:

- `dsr_msgs2`
- `dsr_controller2`
- `dsr_hardware2`
- `dsr_common2`
- `dsr_bringup2`
- `dsr_description2`

Gazebo 사용 시 추가:

- `dsr_gazebo2`

## 권장 Workspace 구조

예시:

```text
jarvis_ws/
  src/
    doosan-robot2/
      dsr_msgs2/
      dsr_controller2/
      dsr_hardware2/
      dsr_common2/
      dsr_bringup2/
      dsr_description2/
      dsr_gazebo2/
      ...
    jarvis/
      package.xml
      setup.py
      setup.cfg
      resource/
      jarvis/
      launch/
```

이 저장소는 workspace의 `src/jarvis` 위치에 clone하는 것을 권장합니다.

## 설치

workspace 생성:

```bash
mkdir -p ~/jarvis_ws/src
cd ~/jarvis_ws/src
```

Doosan ROS2 패키지를 먼저 준비합니다. 팀에서 사용하는 Doosan repo를 clone하거나 기존 `doosan-robot2` 폴더를 복사합니다.

그 다음 이 패키지를 clone합니다:

```bash
cd ~/jarvis_ws/src
git clone https://github.com/ROS2JARVIS/Azas.git jarvis
```

전체 workspace 빌드:

```bash
cd ~/jarvis_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

`jarvis` 패키지만 다시 빌드:

```bash
cd ~/jarvis_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select jarvis
source install/setup.bash
```

패키지 인식 확인:

```bash
ros2 pkg prefix jarvis
```

정상 예시:

```text
/home/<user>/jarvis_ws/install/jarvis
```

## 패키지 구조

```text
jarvis/
  package.xml
  setup.py
  setup.cfg
  resource/
    jarvis
  jarvis/
    __init__.py
    <feature_node>.py
  launch/
    <feature>.launch.py
```

각 기능은 보통 다음 두 파일을 추가해 구성합니다:

```text
jarvis/<feature_node>.py
launch/<feature>.launch.py
```

새 node를 추가하면 `setup.py`의 `console_scripts`에 entry point를 추가해야 합니다.

예시:

```python
entry_points={
    "console_scripts": [
        "my_feature_node = jarvis.my_feature_node:main",
    ],
}
```

그 뒤 다시 빌드합니다:

```bash
cd ~/jarvis_ws
colcon build --packages-select jarvis
source install/setup.bash
```

## 실행 방식

Doosan virtual robot bringup 예시:

```bash
source /opt/ros/humble/setup.bash
source ~/jarvis_ws/install/setup.bash
ros2 launch dsr_bringup2 dsr_bringup2_moveit.launch.py mode:=virtual model:=m0609
```

`jarvis` 패키지의 launch 실행 예시:

```bash
source /opt/ros/humble/setup.bash
source ~/jarvis_ws/install/setup.bash
ros2 launch jarvis <feature>.launch.py
```

현재 포함된 launch 파일 확인:

```bash
ros2 pkg prefix jarvis
ls ~/jarvis_ws/install/jarvis/share/jarvis/launch
```

## Namespace 확인

Doosan launch 설정에 따라 서비스가 namespace 아래에 생성될 수 있습니다.

서비스 확인:

```bash
ros2 service list
```

예:

```text
/motion/move_line
/dsr01/motion/move_line
```

node나 launch에서 Doosan 서비스를 직접 호출하는 경우, 실제 서비스 namespace와 코드의 service prefix가 일치해야 합니다.

## Git 작업 흐름

기능 작업 전 최신 main을 받습니다:

```bash
git checkout main
git pull
```

기능별 브랜치를 만듭니다:

```bash
git checkout -b feature/<feature-name>
```

작업 후:

```bash
git add .
git commit -m "Add <feature-name>"
git push -u origin feature/<feature-name>
```

GitHub에서 Pull Request를 만들어 main에 병합합니다.

## Troubleshooting

`Package 'jarvis' not found`

```bash
source /opt/ros/humble/setup.bash
source ~/jarvis_ws/install/setup.bash
ros2 pkg prefix jarvis
```

다른 workspace가 먼저 잡히면 새 터미널에서 다시 source 하거나, source 순서를 확인합니다.

`ModuleNotFoundError: No module named 'dsr_msgs2'`

Doosan message package가 빌드/source되지 않은 상태입니다.

```bash
cd ~/jarvis_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select dsr_msgs2 jarvis
source install/setup.bash
```

Doosan 서비스가 보이지 않을 때:

```bash
ros2 service list | grep motion
```

bringup launch가 실행 중인지, namespace가 있는지 확인합니다.
