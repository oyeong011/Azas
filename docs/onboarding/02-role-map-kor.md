# 역할별 패키지 맵

이 문서는 협업자가 자기 담당 영역과 건드리면 안 되는 경계를 빠르게 찾기 위한 지도입니다.

## 패키지별 책임

| 패키지 | 담당 영역 | 주요 파일/경계 |
|--------|----------|----------------|
| `azas_interfaces` | 공용 메시지, 서비스, 액션 계약 | `msg/`, `srv/`, `action/PickAndAlign.action` |
| `azas_voice` | STT 텍스트를 상징적 레시피 결정으로 변환 | `command_parser.py`, `recipe_catalog.py`, `recipe_mapper_node.py` |
| `azas_task_manager` | 레시피 결정과 컵 탐지를 태스크 단계로 조합 | `cocktail_dryrun_sequence_node.py`, `cocktail_workflow_plan.py`, `pick_and_align_action_server.py` |
| `azas_perception` | 컵 탐지, 깊이 투영, base_link 기준 컵 자세 발행 | `yolo_tumbler_detector_node.py`, `cup_detection_pose_bridge_node.py` |
| `azas_motion` | 정렬/픽 계획 계산과 모션 실행 경계 | `alignment.py`, `alignment_executor_node.py` |
| `azas_gripper` | RG2 그리퍼 서비스 경계 | `rg2_gripper_node.py` |
| `azas_calibration` | 실측 캘리브레이션 값 로드/저장 경계 | `calibration_loader_node.py`, `calibration.yaml` |
| `azas_bringup` | 런치 파일과 시스템 설정 조합 | `launch/`, `config/` |

## 룰베이스 담당 범위

룰베이스 담당자는 기본적으로 `azas_voice` 안에서 작업합니다.

안전한 수정 범위:

- 한국어 명령 alias 추가
- 레시피 ID alias 추가
- 색상/디스펜서 ID alias 추가
- 취소/확인 단어 보강
- `test_command_parser.py` 테스트 추가

주의가 필요한 수정 범위:

- `/azas/voice/recipe_decision` JSON 필드 변경
- `cocktail_dryrun_sequence_node.py`의 blocked 조건 변경
- `cocktail_workflow_plan.py` 단계 순서 변경

금지 범위:

- 컵 좌표 생성
- 로봇 TCP 좌표 생성
- 캘리브레이션 값 생성
- 모션 게이트 우회

## 룰베이스 데이터 흐름

```text
/stt_result
  -> azas_voice.recipe_mapper_node
  -> azas_voice.command_parser.parse_recipe_command()
  -> /azas/voice/recipe_decision
  -> azas_task_manager.cocktail_dryrun_sequence_node
  -> /azas/cocktail/task_plan
  -> /azas/cocktail/status
```

룰베이스는 “무슨 칵테일을 만들지”와 “어떤 디스펜서를 사용할지”까지만 결정합니다. 실제 컵 위치, 로봇 자세, 그리퍼 동작은 다른 패키지의 안전 경계를 통과해야 합니다.

## PR 분리 기준

| 변경 내용 | 권장 PR 범위 |
|----------|--------------|
| 한국어 명령/레시피 alias | `azas_voice` 단독 |
| 태스크 단계 추가 | `azas_task_manager` 단독 |
| 컵 탐지/pose 발행 변경 | `azas_perception` 단독 |
| 모션 계획 변경 | `azas_motion` 단독, 안전 리뷰 필요 |
| 캘리브레이션 값 변경 | 실측 근거 문서 포함, 안전 리뷰 필요 |
| 런치/설정 변경 | `azas_bringup` 단독 또는 관련 패키지와 분리 |

## 리뷰 때 확인할 질문

- 이 변경이 좌표나 캘리브레이션 값을 새로 만들고 있지 않은가?
- 룰베이스 출력은 여전히 상징 정보만 담고 있는가?
- 실패할 때 blocked 또는 명시적 오류로 멈추는가?
- 하드웨어 영향이 있다면 안전 게이트와 검증 절차가 문서화됐는가?
