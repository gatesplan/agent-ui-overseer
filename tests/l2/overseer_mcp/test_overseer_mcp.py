import json

from project_manager.l0.project_spec import ProjectSpec
from project_manager.l2.overseer_mcp import OverseerMcp

SPEC = {
    'title': '가게',
    'summary': '주문을 받는 앱',
    'terms': [{'word': '주문', 'meaning': '고른 상품 묶음'}],
    'components': [
        {'name': '장바구니',
         'descs': ['고른 상품을 모아 둔다'],
         'mocks': [{'name': '시안', 'href': 'mocks/cart.html'}],
         'does': ['상품을 담는다', {'text': '수량을 합친다', 'then': ['합계를 다시 계산한다']}],
         'donts': ['결제는 하지 않는다'],
         'children': [{'name': '쿠폰', 'donts': ['쿠폰 여러 장은 쓰지 않는다']}]},
        {'name': '결제'},
    ],
}


def tools(tmp_path, spec=SPEC) -> OverseerMcp:
    if spec is not None:
        (tmp_path / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
    return OverseerMcp(object(), ProjectSpec(tmp_path))


def stored(tmp_path):
    return json.loads((tmp_path / 'spec.json').read_text(encoding='utf-8'))


# 스펙 전체를 개체 번호가 붙은 들여쓰기 글로 본다. at 을 주면 그 아래만, 이어진 자리를 머리에 붙여 본다
def test_view_whole_spec_and_subtree(tmp_path):
    mcp = tools(tmp_path)
    assert mcp.spec_view() == '\n'.join([
        'title: 가게',
        'summary: 주문을 받는 앱',
        'w1 주문: 고른 상품 묶음',
        'c1 장바구니',
        '  c1.d1 고른 상품을 모아 둔다',
        '  c1.c1 쿠폰',
        '    c1.c1.n1 쿠폰 여러 장은 쓰지 않는다',
        '  c1.m1 시안 | mocks/cart.html',
        '  c1.f1 상품을 담는다',
        '  c1.f2 수량을 합친다',
        '    c1.f2.f1 합계를 다시 계산한다',
        '  c1.n1 결제는 하지 않는다',
        'c2 결제',
    ])
    assert mcp.spec_view('c1.c1') == 'c1 장바구니\nc1.c1 쿠폰\n  c1.c1.n1 쿠폰 여러 장은 쓰지 않는다'
    assert mcp.spec_view('c1.f2') == 'c1 장바구니\nc1.f2 수량을 합친다\n  c1.f2.f1 합계를 다시 계산한다'
    assert mcp.spec_view('c1.n1').startswith('실패:')
    assert mcp.spec_view('c9').startswith('실패:')
    assert mcp.spec_view('x1').startswith('실패:')


# 번호로 더하고 고치고 지운다. 돌려주는 글에 새 번호와 바뀐 글이 있다
def test_add_edit_remove_by_number(tmp_path):
    mcp = tools(tmp_path)
    assert mcp.spec_add('c2', 'do', ' 카드 결제를 받는다 ') == '더함: c2.f1 카드 결제를 받는다'
    assert mcp.spec_add('', 'term', '손님: 주문하는 사람') == '더함: w2 손님: 주문하는 사람'
    assert mcp.spec_add('c1.f1', 'do', '재고를 잡아 둔다') == '더함: c1.f1.f1 재고를 잡아 둔다'
    assert mcp.spec_add('c2', 'mock', '결제 화면 | https://example.com/pay') == '더함: c2.m1 결제 화면 | https://example.com/pay'
    assert mcp.spec_edit('c1', '카트') == 'c1: "장바구니" → "카트"'
    assert mcp.spec_edit('c1.f2', '같은 상품은 합친다') == 'c1.f2: "수량을 합친다" → "같은 상품은 합친다"'
    assert mcp.spec_edit('w1', '주문: 손님이 고른 상품') == 'w1: "주문: 고른 상품 묶음" → "주문: 손님이 고른 상품"'
    assert mcp.spec_edit('title', '가게 2호점') == 'title: "가게" → "가게 2호점"'
    assert mcp.spec_remove('c1.f2.f1').startswith('지움: c1.f2.f1 "합계를 다시 계산한다"')
    s = stored(tmp_path)
    assert s['title'] == '가게 2호점'
    assert s['terms'] == [{'word': '주문', 'meaning': '손님이 고른 상품'}, {'word': '손님', 'meaning': '주문하는 사람'}]
    assert s['components'][0]['name'] == '카트'
    assert s['components'][0]['does'] == [{'text': '상품을 담는다', 'then': ['재고를 잡아 둔다']}, '같은 상품은 합친다']
    assert s['components'][1] == {'name': '결제', 'does': ['카드 결제를 받는다'], 'mocks': [{'name': '결제 화면', 'href': 'https://example.com/pay'}]}


# 설명은 d 번호로 더하고 고친다
def test_desc_by_number(tmp_path):
    mcp = tools(tmp_path)
    assert mcp.spec_add('c2', 'desc', '주문 값을 받는다') == '더함: c2.d1 주문 값을 받는다'
    assert mcp.spec_edit('c1.d1', '손님이 고른 상품을 모아 둔다') == 'c1.d1: "고른 상품을 모아 둔다" → "손님이 고른 상품을 모아 둔다"'
    assert mcp.spec_add('', 'desc', '프로젝트 아래 설명').startswith('실패:')
    assert stored(tmp_path)['components'][1]['descs'] == ['주문 값을 받는다']


# 개체를 자식째 다른 개체 아래로 옮긴다. 돌려주는 글에 새 번호가 있다
def test_move_by_number(tmp_path):
    mcp = tools(tmp_path)
    assert mcp.spec_move('c1.f2', 'c2').startswith('옮김: c1.f2 → c2.f1 수량을 합친다')
    assert stored(tmp_path)['components'][1]['does'] == [{'text': '수량을 합친다', 'then': ['합계를 다시 계산한다']}]
    assert mcp.spec_move('c1.c1', '').startswith('옮김: c1.c1 → c3 쿠폰')
    assert mcp.spec_move('c1', 'c2').startswith('옮김: c1 → c1.c1 장바구니')
    before = (tmp_path / 'spec.json').read_text(encoding='utf-8')
    assert mcp.spec_move('c1', 'c1.c1').startswith('실패:')
    assert mcp.spec_move('c1.c1.n1', 'c1.f1').startswith('실패:')
    assert mcp.spec_move('c9', 'c1').startswith('실패:')
    assert (tmp_path / 'spec.json').read_text(encoding='utf-8') == before


def test_refusals_come_back_as_failure_text(tmp_path):
    mcp = tools(tmp_path)
    before = (tmp_path / 'spec.json').read_text(encoding='utf-8')
    assert '자식이 있는' in mcp.spec_remove('c1')
    assert mcp.spec_add('c1.n1', 'do', '금지 아래 기능').startswith('실패:')
    assert mcp.spec_add('', 'term', '뜻 없는 용어').startswith('실패:')
    assert mcp.spec_edit('c1', ' ').startswith('실패:')
    assert mcp.spec_edit('c1.f9', '없는 기능').startswith('실패:')
    assert (tmp_path / 'spec.json').read_text(encoding='utf-8') == before
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert tools(empty, None).spec_view() == '실패: 이 프로젝트에 spec.json 이 없다'
