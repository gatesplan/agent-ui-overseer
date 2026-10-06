from project_manager.l1.item_splitter import ItemSplitter


def test_split_items_and_preamble():
    text = (
        "검토했습니다.\n\n"
        "### [질문] 가격은 어떻게 할까요\n"
        "- A: 유지\n"
        "### [제안] save() 수정\n"
        "with 문으로 바꾼다\n"
    )
    preamble, items = ItemSplitter().split(text)
    assert preamble == "검토했습니다."
    assert [(i.kind, i.title) for i in items] == [("질문", "가격은 어떻게 할까요"), ("제안", "save() 수정")]
    assert items[0].body == "- A: 유지"
    assert items[1].body == "with 문으로 바꾼다"


def test_heading_inside_fence_is_body():
    text = "### [보고] 예시\n```\n### [질문] 코드 안 제목\n```\n"
    _, items = ItemSplitter().split(text)
    assert len(items) == 1
    assert "### [질문] 코드 안 제목" in items[0].body


def test_parent_reference_and_unknown_kind():
    text = "### [질문] 합산 시 가격 처리 (← #1-4)\n### [메모] 기타\n"
    _, items = ItemSplitter().split(text)
    assert items[0].title == "합산 시 가격 처리"
    assert items[0].parent == "1-4"
    assert items[1].known_kind is False
    assert items[1].parent is None


def test_no_heading_is_all_preamble():
    preamble, items = ItemSplitter().split("그냥 짧은 대답")
    assert preamble == "그냥 짧은 대답"
    assert items == []
