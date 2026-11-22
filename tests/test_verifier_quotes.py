from extractor import ActionItem, ThreadResult
from thread_parser import Message
from verifier import check_quotes, build_claims


def _res(quote, src=1):
    a = ActionItem(task="t", owner="Bob", deadline="None", source_msg_id=src,
                   supporting_quote=quote, status="open")
    return ThreadResult(summary="One. Two.", decisions=["d"], action_items=[a])


MSGS = [Message(1, "A", "d", "Bob,   please\nhandle the REPORT by Friday.")]


def test_quote_match_ignores_case_and_whitespace():
    assert check_quotes(_res("bob, please handle the report"), MSGS) == [True]


def test_fabricated_quote_or_wrong_message_fails():
    assert check_quotes(_res("Dave will finish it tomorrow"), MSGS) == [False]
    assert check_quotes(_res("Bob, please handle the report", src=9), MSGS) == [False]


def test_claims_cover_summary_decisions_and_items():
    claims = build_claims(_res("x"))
    assert len(claims) == 2 + 1 + 1              # 2 summary sentences, 1 decision, 1 item
