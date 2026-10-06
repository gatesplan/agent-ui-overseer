# agent-ui-overseer

CLI 코딩 에이전트(Claude Code 등) 세션을 탭으로 다루고, 에이전트 응답을 사안 단위 카드로 쪼개 답변·보류·기각으로 처리하는 개인용 UI.

공식 CLI 바이너리를 그대로 띄우고 훅과 대화 기록만 읽는다. 구독 토큰을 꺼내거나 바이너리를 고치지 않는다.

## 구성

- `docs/item-protocol.md`: 에이전트에게 주는 사안 출력 규약. `### [질문|제안|보고] 제목` 단위로 응답을 쓰게 한다
- `scripts/capture_hook.py`: Claude Code Stop 훅. 턴이 끝날 때 응답을 사안으로 쪼개 `data/captures/<session_id>.jsonl`에 쌓는다
- `src/project_manager/`: 캡처 로직 (Ln 구조)
- `web/`: UI 목업 (Overseer, FutureIndustryTheme). 턴을 좌에서 우로 흐르는 기둥으로, 사안 관계를 선으로 그린다

## 목업 실행

```bash
python -m http.server 47310 --bind 127.0.0.1 --directory web
```

## 상태

목업 단계. 실제 PTY 연결, 캡처 데이터 실시간 연동은 아직 없다.
