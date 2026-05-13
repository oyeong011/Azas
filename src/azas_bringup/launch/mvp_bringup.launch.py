from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """MVP-1 skeleton launch: perception, calibration, gripper, motion, task action."""
    return LaunchDescription(
        [
            Node(
                package="azas_perception",
                executable="tumbler_detector_node",
                name="tumbler_detector_node",
                output="screen",
            ),
            Node(
                package="azas_calibration",
                executable="calibration_loader_node",
                name="calibration_loader_node",
                output="screen",
            ),
            Node(
                package="azas_gripper",
                executable="rg2_gripper_node",
                name="rg2_gripper_node",
                output="screen",
            ),
            Node(
                package="azas_motion",
                executable="alignment_executor_node",
                name="alignment_executor_node",
                output="screen",
            ),
            Node(
                package="azas_task_manager",
                executable="pick_and_align_action_server",
                name="pick_and_align_action_server",
                output="screen",
            ),
        ]
    )
