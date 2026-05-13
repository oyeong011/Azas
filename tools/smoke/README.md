# tools/smoke/

가짜 하드웨어 기반 자동화 스모크 테스트 모음입니다.

## 규칙

- 실제 로봇 모션 절대 금지
- 반복 실행 가능해야 합니다
- 가짜 RG2/Doosan 서비스는 파일명과 출력에 명확히 표시
- 라이브 하드웨어가 필요한 테스트는 `checks/`로 이동

## 스크립트 목록

| 스크립트 | 설명 |
|----------|------|
| `smoke_pick_and_align_no_motion.sh` | 픽앤얼라인 액션 비-모션 스모크 |
| `smoke_control_path.sh` | 제어 경로 엔드투엔드 스모크 |
| `smoke_fake_hardware_path.sh` | 가짜 하드웨어 서비스 스모크 |
| `smoke_cocktail_dryrun_sequence.sh` | 칵테일 드라이런 시퀀스 스모크 |
| `smoke_cocktail_dryrun_sequence.py` | 칵테일 드라이런 (Python) |
| `smoke_random_cup_grasp_candidates.sh` | 랜덤 컵 그라스프 후보 스모크 |
| `smoke_real_motion_config_gate.sh` | 실제 모션 설정 게이트 스모크 |
| `smoke_real_motion_entrypoint_gates.sh` | 실제 모션 진입점 게이트 스모크 |
| `smoke_robot_connection_acceptance_gate.sh` | 로봇 연결 수락 게이트 스모크 |
| `smoke_stage_execution_modes.sh` | 스테이지 실행 모드 스모크 |
| `smoke_tumbler_shake_sequence.sh` | 텀블러 쉐이크 시퀀스 스모크 |
| `smoke_dispense_lid_sequence.sh` | 디스펜스·뚜껑 시퀀스 스모크 |
| `fake_hardware_services.py` | 가짜 하드웨어 서비스 서버 (수동 시작) |

## 가짜 서비스 시작

스모크 테스트 실행 전 별도 터미널에서 가짜 서비스를 시작하세요:

```bash
source /opt/ros/humble/setup.bash
source /home/ssu/Azas/install/setup.bash
python3 tools/smoke/fake_hardware_services.py
```
