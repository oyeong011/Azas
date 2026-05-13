# tools/

현장 운용 도구 모음입니다. 역할별 서브디렉토리로 정리되어 있습니다.

## 서브디렉토리 구조

| 디렉토리 | 설명 |
|----------|------|
| `checks/` | 비-모션 상태 점검 스크립트 (하드웨어 명령 없음) |
| `smoke/` | 가짜 하드웨어 기반 자동화 스모크 테스트 |
| `run/` | 현장 실행 스크립트 (드라이런 · 실제 모션 · 복구) |
| `pick/` | 컵 픽 · 사이드 그라스프 플래닝 도구 |
| `perception/` | 인식 데이터 수집 · 프레임 추출 도구 |
| `gazebo_models/` | Gazebo 프리뷰 모델 |

## 현장 투입 핵심 명령어

```bash
# 비-하드웨어 전체 점검
bash tools/checks/verify_control_readiness.sh

# 드라이런
bash tools/run/run_robot_dryrun.sh

# 엄격 게이트 (실제 모션 전 필수)
STRICT=true GATE_STAMP=/tmp/azas_live_hardware_gates_passed \
  bash tools/checks/check_live_hardware_gates.sh

# 실제 모션
bash tools/run/run_robot_real.sh
```

> 전체 명령어 목록은 루트의 **[COMMANDS.md](../COMMANDS.md)** 를 참고하세요.

## 파일 추가 규칙

- 새 구현 파일은 반드시 적절한 서브디렉토리에 넣으세요.
- 루트에는 **안정적인 공개 진입점**만 허용합니다.
- 실제 모션 스크립트는 `--enable-real-motion` 플래그와 확인 문구가 필수입니다.
- 스모크 테스트는 실제 로봇 모션을 포함하지 않아야 합니다.

## 컵 픽 도구 진입점

```bash
# 감독 하에 실제 단일 컵 픽 (도움말)
python3 tools/pick/run_supervised_real_single_cup_pick.py --help

# 사이드 그라스프 후보 스윕
python3 tools/pick/sweep_side_grasp_planning_candidates.py \
  --planning-group manipulator \
  --ee-link tool0 \
  --cup-reference-x 0.42 \
  --cup-reference-y -0.24 \
  --cup-reference-z 0.05 \
  --max-candidates 100
```
