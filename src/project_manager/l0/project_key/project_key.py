import os


# 프로젝트 구분 키. 같은 폴더면 대소문자, 구분자, 상대 경로가 달라도 같은 키다
# 기록 저장소, 세션 이력, 탭, 모듈 지도가 모두 이 키로 같은 프로젝트를 알아본다
class ProjectKey:
    @staticmethod
    def of(path: str) -> str:
        return os.path.normcase(os.path.abspath(path))
