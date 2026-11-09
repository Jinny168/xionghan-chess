from xionghan_chess.desktop.snapshot_guard import should_accept_snapshot


def test_stale_snapshot_in_same_room_is_rejected():
    assert not should_accept_snapshot("R1", 7, "R1", 6)


def test_duplicate_snapshot_in_same_room_is_accepted():
    assert should_accept_snapshot("R1", 7, "R1", 7)


def test_forward_snapshot_in_same_room_is_accepted():
    assert should_accept_snapshot("R1", 7, "R1", 8)


def test_snapshot_from_new_room_is_accepted_even_with_lower_revision():
    assert should_accept_snapshot("R1", 42, "R2", 0)


def test_none_room_is_treated_as_a_distinct_room():
    assert should_accept_snapshot("R1", 10, None, 0)
