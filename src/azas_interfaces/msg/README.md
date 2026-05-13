# azas_interfaces messages

These interfaces are MVP-1 contracts derived from `wiki/syntheses/ROS 2 Package Architecture.md`.
They intentionally exclude recipe/LLM coordinate outputs.


## External grasp candidates

`GraspCandidate` and `GraspCandidateArray` are adapter contracts for external grasp generators such as AnyGrasp, Contact-GraspNet, or GPD. They carry candidate poses only. They do not authorize robot motion.

Before `PickAndAlign` can use a candidate, Azas must verify frame freshness, transform to `base_link`, workspace limits, collision geometry, gripper compatibility, and MoveIt feasibility.
