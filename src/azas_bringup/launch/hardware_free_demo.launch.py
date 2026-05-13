from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    selected_dispenser_id = LaunchConfiguration("selected_dispenser_id")
    use_rviz = LaunchConfiguration("use_rviz")
    run_live_stt = LaunchConfiguration("run_live_stt")
    use_llm = LaunchConfiguration("use_llm")
    cup_detection_topic = LaunchConfiguration("cup_detection_topic")
    tumbler_pose_topic = LaunchConfiguration("tumbler_pose_topic")

    scene_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("jarvis"), "launch", "tumbler_dispenser_scene.launch.py"])
        ),
        launch_arguments={
            "use_rviz": use_rviz,
            "selected_dispenser_id": selected_dispenser_id,
        }.items(),
    )

    floor_place_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("jarvis"), "launch", "tumbler_floor_place.launch.py"])
        ),
        launch_arguments={
            "selected_dispenser_id": selected_dispenser_id,
            "use_tumbler_pose_topic": "true",
            "tumbler_pose_topic": tumbler_pose_topic,
            "allow_demo_tumbler_position_fallback": "false",
            "tumbler_pose_wait_timeout": LaunchConfiguration("tumbler_pose_wait_timeout"),
            "enable_hardware": "false",
            "hardware_confirm": "",
            "allow_service_control_without_moveit": "false",
            "execution_stage": LaunchConfiguration("execution_stage"),
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("selected_dispenser_id", default_value="2"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("run_live_stt", default_value="false"),
            DeclareLaunchArgument("use_llm", default_value="false"),
            DeclareLaunchArgument("enable_llm", default_value="false"),
            DeclareLaunchArgument("llm_model", default_value="gpt-4o-mini"),
            DeclareLaunchArgument("llm_base_url", default_value="https://api.openai.com/v1"),
            DeclareLaunchArgument("llm_api_key_env", default_value="OPENAI_API_KEY"),
            DeclareLaunchArgument("stt_topic", default_value="/stt_result"),
            DeclareLaunchArgument("cup_detection_topic", default_value="/azas/demo/cup_detection"),
            DeclareLaunchArgument("tumbler_pose_topic", default_value="/azas/demo/tumbler_pose"),
            DeclareLaunchArgument("tumbler_pose_wait_timeout", default_value="8.0"),
            DeclareLaunchArgument("execution_stage", default_value="full"),
            DeclareLaunchArgument("frame_id", default_value="base_link"),
            DeclareLaunchArgument("confidence", default_value="0.95"),
            DeclareLaunchArgument("grasp_x", default_value="0.42"),
            DeclareLaunchArgument("grasp_y", default_value="-0.24"),
            DeclareLaunchArgument("grasp_z", default_value="0.05"),
            DeclareLaunchArgument("mouth_x", default_value="0.42"),
            DeclareLaunchArgument("mouth_y", default_value="-0.24"),
            DeclareLaunchArgument("mouth_z", default_value="0.22"),
            scene_launch,
            Node(
                package="azas_voice",
                executable="stt_node",
                name="stt_node",
                output="screen",
                parameters=[{"stt_topic": LaunchConfiguration("stt_topic")}],
                condition=IfCondition(run_live_stt),
            ),
            Node(
                package="azas_voice",
                executable="recipe_mapper_node",
                name="recipe_mapper_node",
                output="screen",
                parameters=[{"stt_topic": LaunchConfiguration("stt_topic")}],
                condition=UnlessCondition(use_llm),
            ),
            Node(
                package="azas_voice",
                executable="llm_recipe_mapper_node",
                name="llm_recipe_mapper_node",
                output="screen",
                parameters=[
                    {
                        "stt_topic": LaunchConfiguration("stt_topic"),
                        "enable_llm": ParameterValue(LaunchConfiguration("enable_llm"), value_type=bool),
                        "model": LaunchConfiguration("llm_model"),
                        "base_url": LaunchConfiguration("llm_base_url"),
                        "api_key_env": LaunchConfiguration("llm_api_key_env"),
                    }
                ],
                condition=IfCondition(use_llm),
            ),
            Node(
                package="azas_perception",
                executable="simulated_cup_detection_node",
                name="simulated_cup_detection_node",
                output="screen",
                parameters=[
                    {
                        "output_topic": cup_detection_topic,
                        "frame_id": LaunchConfiguration("frame_id"),
                        "confidence": ParameterValue(LaunchConfiguration("confidence"), value_type=float),
                        "publish_once": False,
                        "grasp_x": ParameterValue(LaunchConfiguration("grasp_x"), value_type=float),
                        "grasp_y": ParameterValue(LaunchConfiguration("grasp_y"), value_type=float),
                        "grasp_z": ParameterValue(LaunchConfiguration("grasp_z"), value_type=float),
                        "mouth_x": ParameterValue(LaunchConfiguration("mouth_x"), value_type=float),
                        "mouth_y": ParameterValue(LaunchConfiguration("mouth_y"), value_type=float),
                        "mouth_z": ParameterValue(LaunchConfiguration("mouth_z"), value_type=float),
                    }
                ],
            ),
            Node(
                package="azas_perception",
                executable="cup_detection_pose_bridge_node",
                name="demo_cup_pose_bridge_node",
                output="screen",
                parameters=[
                    {
                        "input_topic": cup_detection_topic,
                        "output_topic": tumbler_pose_topic,
                        "min_confidence": ParameterValue(LaunchConfiguration("confidence"), value_type=float),
                        "target_frame": LaunchConfiguration("frame_id"),
                        "require_tf": False,
                    }
                ],
            ),
            TimerAction(period=2.0, actions=[floor_place_launch]),
        ]
    )
