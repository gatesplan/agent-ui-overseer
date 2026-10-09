from project_manager.l1.map_watcher import MapWatcher


# 서명과 지도를 손으로 정하는 가짜 ModuleMap
class FakeMaps:
    def __init__(self):
        self.sigs: dict[str, tuple] = {}
        self.scans = 0

    def signature(self, cwd):
        return self.sigs.get(str(cwd), (0, 0, 0))

    def scan(self, cwd):
        self.scans += 1
        return {'status': 'ok', 'map': {'n': self.scans}}


def test_get_scans_once_then_changed_reports_only_edited_folders(tmp_path):
    a, b = str(tmp_path / 'a'), str(tmp_path / 'b')
    maps = FakeMaps()
    watcher = MapWatcher(maps)
    assert watcher.get(a) == {'status': 'ok', 'map': {'n': 1}}
    assert watcher.get(a.upper() if a[1] == ':' else a) == {'status': 'ok', 'map': {'n': 1}}
    watcher.get(b)
    assert maps.scans == 2
    assert watcher.changed() == []
    maps.sigs[a] = (1, 5, 10)
    assert watcher.changed() == [(a, {'status': 'ok', 'map': {'n': 3}})]
    assert watcher.changed() == []
    assert watcher.get(a) == {'status': 'ok', 'map': {'n': 3}}


def test_keep_only_stops_watching_closed_folders(tmp_path):
    a, b = str(tmp_path / 'a'), str(tmp_path / 'b')
    maps = FakeMaps()
    watcher = MapWatcher(maps)
    watcher.get(a)
    watcher.get(b)
    watcher.keep_only([b])
    maps.sigs[a] = maps.sigs[b] = (9, 9, 9)
    assert [cwd for cwd, _ in watcher.changed()] == [b]
