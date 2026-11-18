import json

from project_manager.l0.project_spec import ProjectSpec

SPEC = {
    'title': '가게',
    'summary': '주문을 받는 앱',
    'terms': [{'word': '주문', 'meaning': '손님이 고른 상품 묶음'}],
    'components': [
        {'name': '장바구니',
         'mocks': [{'name': '장바구니 화면', 'href': 'mocks/cart.html'}, {'name': '시안', 'href': 'https://example.com/a'}],
         'does': ['같은 상품은 수량을 합친다'],
         'donts': ['결제는 하지 않는다'],
         'open': ['품절 상품을 어떻게 보일지'],
         'children': [{'name': '쿠폰', 'does': ['쿠폰 하나만 적용한다']}]},
    ],
}


def write(tmp_path, data):
    (tmp_path / 'spec.json').write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding='utf-8')


def test_reads_spec_from_project_root(tmp_path):
    write(tmp_path, SPEC)
    assert ProjectSpec(tmp_path).read() == {'status': 'ok', 'spec': SPEC}


def test_missing_file_is_none(tmp_path):
    assert ProjectSpec(tmp_path).read() == {'status': 'none'}


def test_broken_json_is_error_with_reason(tmp_path):
    write(tmp_path, '{"title": ')
    got = ProjectSpec(tmp_path).read()
    assert got['status'] == 'error'
    assert 'spec.json' in got['message']


# 화면에 보이지 않는 칸이 있으면 숨은 설명이 되므로 받지 않는다. 어디가 문제인지 알린다
def test_unknown_field_is_error_naming_where(tmp_path):
    spec = json.loads(json.dumps(SPEC))
    spec['components'][0]['children'][0]['description'] = '숨은 설명'
    write(tmp_path, spec)
    got = ProjectSpec(tmp_path).read()
    assert got['status'] == 'error'
    assert 'components[0].children[0]' in got['message']
    assert 'description' in got['message']


def test_wrong_types_are_errors(tmp_path):
    cases = [
        ['not an object'],
        {'components': [{'does': ['이름 없음']}]},
        {'components': [{'name': '가', 'does': '한 줄이 아닌 목록이어야 한다'}]},
        {'components': [{'name': '가', 'does': [3]}]},
        {'terms': [{'word': '주문'}]},
        {'components': [{'name': '가', 'mocks': [{'name': '주소 없음'}]}]},
        {'components': [{'name': '가', 'mocks': ['문자열 목업']}]},
    ]
    for data in cases:
        write(tmp_path, data)
        got = ProjectSpec(tmp_path).read()
        assert got['status'] == 'error', data


# 하는 것은 이어서 일어나는 일(then)을 달 수 있고, 그 일도 다시 이어질 수 있다
def test_does_line_carries_then_chain(tmp_path):
    spec = {'components': [{'name': '장바구니', 'does': [
        '같은 상품은 수량을 합친다',
        {'text': '상품을 담는다', 'then': ['합계를 다시 계산한다', {'text': '재고를 잡아 둔다', 'then': ['품절이면 알린다']}]},
        {'text': '뒤따르는 일 없는 줄'},
    ]}]}
    write(tmp_path, spec)
    assert ProjectSpec(tmp_path).read() == {'status': 'ok', 'spec': spec}


def test_bad_then_is_error_naming_where(tmp_path):
    cases = [
        ({'components': [{'name': '가', 'does': [{'then': ['글 없음']}]}]}, 'does[0].text'),
        ({'components': [{'name': '가', 'does': [{'text': '담는다', 'then': '목록이 아님'}]}]}, 'does[0].then'),
        ({'components': [{'name': '가', 'does': [{'text': '담는다', 'then': [{'text': '계산한다', 'note': '숨은 설명'}]}]}]}, 'does[0].then[0]'),
        ({'components': [{'name': '가', 'does': [{'text': '담는다', 'then': [3]}]}]}, 'does[0].then[0]'),
    ]
    for data, where in cases:
        write(tmp_path, data)
        got = ProjectSpec(tmp_path).read()
        assert got['status'] == 'error', data
        assert where in got['message'], got['message']


# 이어서 일어나는 일은 실행되는 하는 것에만 단다. 하지 않는 것과 열린 것은 한 줄 글뿐이다
def test_then_only_on_does(tmp_path):
    for key in ('donts', 'open'):
        write(tmp_path, {'components': [{'name': '가', key: [{'text': '줄', 'then': ['뒤']}]}]})
        assert ProjectSpec(tmp_path).read()['status'] == 'error', key


def test_signature_changes_when_file_changes(tmp_path):
    spec = ProjectSpec(tmp_path)
    assert spec.signature() is None
    write(tmp_path, SPEC)
    first = spec.signature()
    assert first is not None
    write(tmp_path, {**SPEC, 'title': '가게 2호점'})
    assert spec.signature() != first
    (tmp_path / 'spec.json').unlink()
    assert spec.signature() is None


def test_mock_file_inside_project(tmp_path):
    (tmp_path / 'mocks').mkdir()
    page = tmp_path / 'mocks' / 'cart.html'
    page.write_text('<p>cart</p>', encoding='utf-8')
    spec = ProjectSpec(tmp_path)
    assert spec.mock_file('mocks/cart.html') == page.resolve()
    assert spec.mock_file('./mocks/cart.html') == page.resolve()
    assert spec.mock_file('mocks\\cart.html') == page.resolve()


# 프로젝트 밖, 점으로 시작하는 폴더와 파일(.git, .env, .overseer), 폴더, 없는 파일은 내주지 않는다
def test_mock_file_refuses_outside_hidden_and_missing(tmp_path):
    project = tmp_path / 'shop'
    project.mkdir()
    (tmp_path / 'secret.txt').write_text('x', encoding='utf-8')
    (project / '.env').write_text('KEY=1', encoding='utf-8')
    (project / '.overseer').mkdir()
    (project / '.overseer' / 'launch.json').write_text('{}', encoding='utf-8')
    (project / 'mocks').mkdir()
    spec = ProjectSpec(project)
    for rel in ['../secret.txt', 'mocks/../../secret.txt', '.env', '.overseer/launch.json', 'mocks', 'mocks/none.html',
                '', str(tmp_path / 'secret.txt'), 'C:secret.txt']:
        assert spec.mock_file(rel) is None, rel


# 스펙 패널에서 사용자가 고친 것 ------------------------------------------------

def stored(tmp_path):
    return json.loads((tmp_path / 'spec.json').read_text(encoding='utf-8'))


def cart_spec():
    return {'title': '가게', 'terms': [{'word': '주문', 'meaning': '고른 상품 묶음'}],
            'components': [{'name': '장바구니', 'does': ['상품을 담는다', {'text': '수량을 합친다', 'then': ['합계를 다시 계산한다']}],
                            'children': [{'name': '쿠폰'}]}]}


# 글 한 칸을 고친다. 고치려던 글이 그대로일 때만 쓰고, 파일 전체를 다시 쓴다
def test_edit_sets_text_when_unchanged(tmp_path):
    write(tmp_path, cart_spec())
    got = ProjectSpec(tmp_path).edit([
        {'path': ['components', 0, 'does', 0], 'old': '상품을 담는다', 'new': '상품을 장바구니에 담는다'},
        {'path': ['components', 0, 'does', 1, 'then', 0], 'old': '합계를 다시 계산한다', 'new': '합계와 할인을 다시 계산한다'},
        {'path': ['terms', 0, 'meaning'], 'old': '고른 상품 묶음', 'new': '손님이 고른 상품 묶음'},
    ])
    assert got['status'] == 'ok'
    spec = stored(tmp_path)
    assert got['spec'] == spec
    assert spec['components'][0]['does'] == ['상품을 장바구니에 담는다', {'text': '수량을 합친다', 'then': ['합계와 할인을 다시 계산한다']}]
    assert spec['terms'][0]['meaning'] == '손님이 고른 상품 묶음'


# 화면이 본 뒤 파일이 바뀌었거나, 없는 자리이거나, 빈 글이면 쓰지 않는다. 여러 칸 중 하나라도 안 되면 하나도 쓰지 않는다
def test_edit_refuses_stale_missing_or_empty(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    before = (tmp_path / 'spec.json').read_text(encoding='utf-8')
    for changes in [
        [{'path': ['components', 0, 'name'], 'old': '장바구니 옛 이름', 'new': '카트'}],
        [{'path': ['components', 3, 'name'], 'old': '장바구니', 'new': '카트'}],
        [{'path': ['components', 0, 'name'], 'old': '장바구니', 'new': '  '}],
        [{'path': ['components', 0, 'children'], 'old': '장바구니', 'new': '카트'}],
        [{'path': ['title'], 'old': '가게', 'new': '가게 2호점'}, {'path': ['components', 0, 'name'], 'old': '틀린 글', 'new': '카트'}],
    ]:
        got = spec.edit(changes)
        assert got['status'] == 'error', changes
        assert got['message']
    assert (tmp_path / 'spec.json').read_text(encoding='utf-8') == before


# 고른 개체 아래에 자식을 더한다. 프로젝트에는 구성요소, 구성요소에는 구성요소와 기능과 하지 않는 것, 기능에는 이어서 일어나는 기능
def test_add_child_under_each_node_kind(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    got = spec.add([], '가게', 'component', '결제')
    assert got['status'] == 'ok' and got['path'] == ['components', 1]
    got = spec.add(['components', 0], '장바구니', 'component', '추천')
    assert got['path'] == ['components', 0, 'children', 1]
    got = spec.add(['components', 0], '장바구니', 'do', '빈 장바구니를 알린다')
    assert got['path'] == ['components', 0, 'does', 2]
    got = spec.add(['components', 0], '장바구니', 'dont', '결제는 하지 않는다')
    assert got['path'] == ['components', 0, 'donts', 0]
    # 한 줄 글이던 기능은 이어지는 일이 생기면 {text, then} 이 된다
    got = spec.add(['components', 0, 'does', 0], '상품을 담는다', 'do', '재고를 잡아 둔다')
    assert got['path'] == ['components', 0, 'does', 0, 'then', 0]
    got = spec.add(['components', 0, 'does', 1, 'then', 0], '합계를 다시 계산한다', 'do', '쿠폰을 다시 맞춘다')
    assert got['path'] == ['components', 0, 'does', 1, 'then', 0, 'then', 0]
    s = stored(tmp_path)
    assert [c['name'] for c in s['components']] == ['장바구니', '결제']
    assert [c['name'] for c in s['components'][0]['children']] == ['쿠폰', '추천']
    assert s['components'][0]['donts'] == ['결제는 하지 않는다']
    assert s['components'][0]['does'] == [
        {'text': '상품을 담는다', 'then': ['재고를 잡아 둔다']},
        {'text': '수량을 합친다', 'then': [{'text': '합계를 다시 계산한다', 'then': ['쿠폰을 다시 맞춘다']}]},
        '빈 장바구니를 알린다',
    ]


def test_add_refuses_wrong_kind_stale_parent_or_empty(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    before = (tmp_path / 'spec.json').read_text(encoding='utf-8')
    for args in [
        ([], '가게', 'do', '프로젝트 바로 아래 기능'),
        ([], '가게', 'dont', '프로젝트 바로 아래 하지 않는 것'),
        (['components', 0, 'does', 0], '상품을 담는다', 'dont', '기능 아래 하지 않는 것'),
        (['components', 0, 'does', 0], '상품을 담는다', 'component', '기능 아래 구성요소'),
        (['terms', 0], '주문', 'do', '용어 아래'),
        (['components', 0], '옛 이름', 'do', '그새 바뀐 부모'),
        (['components', 5], '장바구니', 'do', '없는 부모'),
        (['components', 0], '장바구니', 'do', ''),
        (['components', 0], '장바구니', 'widget', '모르는 종류'),
        (['components', 0], '장바구니', 'mock', '목업은 이름과 경로가 다 있어야 한다'),
        ([], '가게', 'term', {'word': '손님', 'meaning': ' '}),
    ]:
        got = spec.add(*args)
        assert got['status'] == 'error', args
    assert (tmp_path / 'spec.json').read_text(encoding='utf-8') == before


# 순번(at)을 주면 그 자리에 끼운다. 지운 개체를 실행취소로 제자리에 되살릴 때 쓴다
def test_add_at_inserts_in_place(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    got = spec.add(['components', 0], '장바구니', 'do', '빈 장바구니를 알린다', 1)
    assert got['status'] == 'ok' and got['path'] == ['components', 0, 'does', 1]
    assert spec.add(['components', 0], '장바구니', 'dont', '결제는 하지 않는다', 0)['path'] == ['components', 0, 'donts', 0]
    assert spec.add([], '가게', 'term', {'word': '손님', 'meaning': '주문하는 사람'}, 0)['path'] == ['terms', 0]
    # 한 줄 글이던 기능 아래에도 0번에는 끼운다
    assert spec.add(['components', 0, 'does', 0], '상품을 담는다', 'do', '재고를 잡아 둔다', 0)['path'] == ['components', 0, 'does', 0, 'then', 0]
    s = stored(tmp_path)
    assert s['components'][0]['does'] == [{'text': '상품을 담는다', 'then': ['재고를 잡아 둔다']}, '빈 장바구니를 알린다',
                                          {'text': '수량을 합친다', 'then': ['합계를 다시 계산한다']}]
    assert [t['word'] for t in s['terms']] == ['손님', '주문']
    before = (tmp_path / 'spec.json').read_text(encoding='utf-8')
    for at in (4, -1, '1', True):
        assert spec.add(['components', 0], '장바구니', 'do', '목록 밖', at)['status'] == 'error', at
    assert spec.add(['components', 0, 'does', 1], '빈 장바구니를 알린다', 'do', '빈 목록의 1번', 1)['status'] == 'error'
    assert (tmp_path / 'spec.json').read_text(encoding='utf-8') == before


def test_writes_need_a_readable_spec(tmp_path):
    assert ProjectSpec(tmp_path).add([], '', 'component', '첫 구성요소')['status'] == 'error'
    write(tmp_path, '{"title": ')
    assert ProjectSpec(tmp_path).edit([{'path': ['title'], 'old': '', 'new': '가게'}])['status'] == 'error'


# 에이전트 도구가 쓰는 자식: 프로젝트의 용어, 구성요소의 열린 것과 목업
def test_add_terms_open_and_mocks(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    assert spec.add([], '가게', 'term', {'word': ' 손님 ', 'meaning': '주문하는 사람'})['path'] == ['terms', 1]
    assert spec.add(['components', 0], '장바구니', 'open', '품절 상품 표시')['path'] == ['components', 0, 'open', 0]
    assert spec.add(['components', 0], '장바구니', 'mock', {'name': '시안', 'href': 'mocks/cart.html'})['path'] == ['components', 0, 'mocks', 0]
    s = stored(tmp_path)
    assert s['terms'][1] == {'word': '손님', 'meaning': '주문하는 사람'}
    assert s['components'][0]['open'] == ['품절 상품 표시']
    assert s['components'][0]['mocks'] == [{'name': '시안', 'href': 'mocks/cart.html'}]


# 자식이 없는 개체만 지운다. 빈 목록은 키째 지우고, 이어지는 일이 다 없어진 기능은 한 줄 글로 돌아간다
def test_remove_childless_nodes(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    got = spec.remove(['components', 0, 'does', 1, 'then', 0], '합계를 다시 계산한다')
    assert got['status'] == 'ok' and got['path'] == ['components', 0, 'does', 1, 'then', 0]
    assert stored(tmp_path)['components'][0]['does'] == ['상품을 담는다', '수량을 합친다']
    assert spec.remove(['components', 0, 'children', 0], '쿠폰')['status'] == 'ok'
    assert 'children' not in stored(tmp_path)['components'][0]
    assert spec.remove(['terms', 0], '주문')['status'] == 'ok'
    assert 'terms' not in stored(tmp_path)


def test_remove_refuses_parents_root_stale_or_missing(tmp_path):
    write(tmp_path, cart_spec())
    spec = ProjectSpec(tmp_path)
    before = (tmp_path / 'spec.json').read_text(encoding='utf-8')
    for args in [
        (['components', 0], '장바구니'),
        (['components', 0, 'does', 1], '수량을 합친다'),
        ([], '가게'),
        (['title'], '가게'),
        (['components', 0, 'does', 0], '옛 글'),
        (['components', 0, 'does', 7], '상품을 담는다'),
    ]:
        got = spec.remove(*args)
        assert got['status'] == 'error', args
    assert '자식이 있는' in spec.remove(['components', 0], '장바구니')['message']
    assert (tmp_path / 'spec.json').read_text(encoding='utf-8') == before
