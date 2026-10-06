import threading
from collections.abc import Callable

from loguru import logger
from winpty import PtyProcess

# 터미널 창을 다시 열 때 다시 그리려고 남겨 두는 출력 양
HISTORY_LIMIT = 1_000_000


# 의사 터미널(ConPTY)로 띄운 프로세스 하나. 출력은 읽기 스레드가 받아 듣는 쪽에 넘기고 일부를 남겨 둔다
class PtySession:
    def __init__(self, argv: list[str], cwd: str, env: dict[str, str], rows: int = 40, cols: int = 120):
        self.argv = argv
        self.cwd = cwd
        self.env = env
        self.rows, self.cols = rows, cols
        self.listeners: list[Callable[[str], None]] = []
        self.on_exit: Callable[[], None] | None = None
        self._history: list[str] = []
        self._size = 0
        self._lock = threading.Lock()
        self._proc: PtyProcess | None = None

    def start(self) -> None:
        logger.info(f"pty 시작: argv={self.argv}, cwd={self.cwd}")
        self._proc = PtyProcess.spawn(self.argv, cwd=self.cwd, env=self.env, dimensions=(self.rows, self.cols))
        threading.Thread(target=self._read_loop, daemon=True).start()

    @property
    def alive(self) -> bool:
        return bool(self._proc and self._proc.isalive())

    def history(self) -> str:
        with self._lock:
            return ''.join(self._history)

    def write(self, data: str) -> None:
        if self.alive:
            self._proc.write(data)

    # 여러 줄을 한 입력으로 넣는다. 줄바꿈이 제출로 읽히지 않게 bracketed paste 로 감싼다
    def paste(self, text: str) -> None:
        self.write(f'\x1b[200~{text}\x1b[201~')

    def resize(self, rows: int, cols: int) -> None:
        self.rows, self.cols = rows, cols
        if self.alive:
            self._proc.setwinsize(rows, cols)

    def terminate(self) -> None:
        if self.alive:
            logger.info(f"pty 종료: cwd={self.cwd}")
            self._proc.terminate(force=True)

    def _read_loop(self) -> None:
        while True:
            try:
                data = self._proc.read(65536)
            except EOFError:
                break
            if not data:
                continue
            with self._lock:
                self._history.append(data)
                self._size += len(data)
                while self._size > HISTORY_LIMIT and len(self._history) > 1:
                    self._size -= len(self._history.pop(0))
            for listener in list(self.listeners):
                listener(data)
        logger.info(f"pty 끝남: cwd={self.cwd}")
        if self.on_exit:
            self.on_exit()
