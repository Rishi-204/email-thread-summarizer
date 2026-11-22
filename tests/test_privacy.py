from thread_parser import Message
from privacy import mask_messages, has_leftover_placeholders

MSGS = [
    Message(1, "Priya Sharma <priya@x.com>", "d",
            "Rahul, please call +91 98765 43210 about the invoice."),
    Message(2, "Rahul Verma <rahul@x.com>", "d", "Priya, I will call. Mail me at rahul@x.com."),
    Message(3, "Priya Sharma <priya@x.com>", "d", "Thanks Rahul."),
]


def _joined(masked):
    return " ".join(m.sender + " " + m.body for m in masked)


def test_no_real_identifier_is_sent():
    masked, _ = mask_messages(MSGS)
    text = _joined(masked)
    for real in ["Priya", "Rahul", "Sharma", "Verma", "priya@x.com", "rahul@x.com", "98765"]:
        assert real not in text


def test_same_person_same_placeholder_across_messages():
    masked, _ = mask_messages(MSGS)
    assert masked[0].body.split()[0].rstrip(",") == masked[1].sender.split()[0]
    assert masked[2].body.split()[1].rstrip(".") == masked[1].sender.split()[0]


def test_restore_round_trip_has_no_leftovers():
    masked, masker = mask_messages(MSGS)
    restored = masker.restore(_joined(masked))
    assert not has_leftover_placeholders(restored)
    assert "98765" in restored and "rahul@x.com" in restored
