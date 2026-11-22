from thread_parser import parse_thread, clean_body

RAW = """From: Alice <alice@x.com>
Date: 2026-10-01

Hi team, budget report by Friday. Bob, can you handle it?
======
From: Bob <bob@x.com>
Date: 2026-10-01

Sure, I'll do it.

> Hi team, budget report by Friday.

Thanks,
Bob
======
From: Carol <carol@x.com>
Date: 2026-10-02

Sent the Q3 numbers.

-----Original Message-----
From: Bob
Please send the numbers."""


def test_splits_messages_and_ids():
    msgs = parse_thread(RAW)
    assert [m.id for m in msgs] == [1, 2, 3]
    assert msgs[1].sender.startswith("Bob")


def test_strips_quotes_and_signature():
    msgs = parse_thread(RAW)
    assert msgs[1].body == "Sure, I'll do it."


def test_cuts_original_message_block():
    msgs = parse_thread(RAW)
    assert msgs[2].body == "Sent the Q3 numbers."


def test_on_wrote_cut():
    assert clean_body("Done.\nOn Mon, Bob wrote:\nold text") == "Done."
