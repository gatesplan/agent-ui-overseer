# 목업(web/) 정적 서버. 브라우저가 수정 전 js, css 를 캐시에서 쓰지 않게 캐시 금지 헤더를 붙인다
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 47310


# 응답마다 캐시 금지 헤더를 붙이는 정적 파일 핸들러
class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main() -> int:
    handler = partial(NoCacheHandler, directory=str(ROOT / 'web'))
    with ThreadingHTTPServer(('127.0.0.1', PORT), handler) as server:
        print(f"http://127.0.0.1:{PORT}/")
        server.serve_forever()
    return 0


if __name__ == '__main__':
    sys.exit(main())
