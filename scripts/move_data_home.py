# 저장소의 data/ 를 이 컴퓨터의 패널 기록 폴더 ~/.overseer/ 로 옮긴다(탭 DB, 캡처, 로그, 백업)
# 서버를 멈춘 동안 돌린다: pwsh scripts/restart_server.ps1 -WhileStopped scripts/move_data_home.py
# 옮길 곳에 같은 이름이 있으면: 폴더는 안을 합치고, 로그 파일은 옛 내용을 앞에 붙인다. 그 밖의 파일은 옮기지 않고 알린다
# 여러 번 돌려도 된다. data/ 가 비면 지운다
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'data'
# 환경변수가 아니라 고정 경로로 옮긴다. 재시작 스크립트의 프로세스가 어떤 환경을 물려받았는지에 기대지 않게
TARGET = Path.home() / '.overseer'

moved: list[str] = []
left: list[str] = []


def merge(src: Path, dst: Path) -> None:
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append(str(src.relative_to(SOURCE)))
        return
    if src.is_dir() and dst.is_dir():
        for child in list(src.iterdir()):
            merge(child, dst / child.name)
        if not any(src.iterdir()):
            src.rmdir()
        return
    if src.is_file() and dst.is_file() and src.suffix == '.log':
        dst.write_bytes(src.read_bytes() + dst.read_bytes())
        src.unlink()
        moved.append(f'{src.relative_to(SOURCE)} (합침)')
        return
    left.append(str(src.relative_to(SOURCE)))


def main() -> int:
    if not SOURCE.is_dir():
        print(f'옮길 것 없음: {SOURCE} 가 없다')
        return 0
    for entry in list(SOURCE.iterdir()):
        merge(entry, TARGET / entry.name)
    if not any(SOURCE.iterdir()):
        SOURCE.rmdir()
    print(f'옮김 {len(moved)}: {SOURCE} → {TARGET}')
    for name in left:
        print(f'  옮기지 않음(이미 있음): {name}')
    return 1 if left else 0


if __name__ == '__main__':
    sys.exit(main())
