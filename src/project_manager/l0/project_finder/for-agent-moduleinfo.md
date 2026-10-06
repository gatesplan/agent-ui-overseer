---
sources:
  project_finder.py: 388aa5551d8a
---
# project_finder

새 세션 창의 폴더 목록. 드라이브마다 루트의 `Projects` 폴더(`C:\Projects`, `D:\Projects` …)를 찾아 그 안의 프로젝트 폴더를 보여 주고, 새 프로젝트 폴더를 만든다.

## ProjectFinder

### __init__
__init__(folder: str = 'Projects', drives: list[str] | None = None, roots: list[str] | None = None)
    drives 를 주지 않으면 A: ~ Z: 를 본다. 시험에서는 임시 폴더를 드라이브처럼 넘긴다.
    roots 를 주면 드라이브를 훑지 않고 그 폴더들을 프로젝트 루트로 쓴다(서버 --projects, OVERSEER_PROJECTS).

### Methods

roots() -> list[Path]
    있는 프로젝트 루트들.
default_root() -> Path
    새 폴더를 만들 기본 위치. 첫 루트. 하나도 없으면 정한 첫 루트, 그것도 없으면 첫 드라이브의 Projects(만들 때 생긴다).
scan() -> list[dict]
    [{root, dirs: [{name, path}]}]. 폴더는 최근 수정 순. 점으로 시작하는 폴더는 뺀다.
create(root: str, name: str) -> Path
    raise ValueError    # 이름에 경로 구분자나 금지 글자가 있거나, root 가 Projects 폴더가 아닐 때
    root 안에 name 폴더를 만든다. 이미 있으면 그대로 돌려준다.

## 설계 이유

- 만들 위치를 Projects 폴더로만 받는다. 화면에서 넘어온 값으로 아무 곳에나 폴더를 만들지 않게 하려는 것.
- 다른 위치의 폴더는 화면에서 전체 경로로 연다(만들지 않는다).
