# Azas Agent Guide

This repository is a ROS 2 Humble robotics project. Follow `/home/ssu/LLM_WIKI.md` for wiki maintenance rules.

## Project Rules

- Treat `wiki/` as the compiled project knowledge base.
- Do not commit runtime state such as `.omx/`, `build/`, `install/`, or `log/`.
- Keep LLM/VLA output limited to user intent and recipe selection. Robot coordinates must come from calibrated vision/config data.
- Hardware-affecting changes must document safety assumptions, speed limits, failure behavior, and verification steps.
- Prefer small GitHub issues and PRs split by module: vision, calibration, robot motion, gripper, AI, bringup, integration.

