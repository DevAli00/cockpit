from app.core.ratelimit import SlidingWindowLimiter


def test_blocks_after_limit_and_recovers_after_window() -> None:
    now = [1000.0]
    lim = SlidingWindowLimiter(limit=3, window_s=60, clock=lambda: now[0])
    assert all(lim.hit("ip") for _ in range(3))
    assert not lim.hit("ip")
    assert lim.hit("other")  # keys are independent
    now[0] += 61
    assert lim.hit("ip")


def test_reset_clears_a_key() -> None:
    lim = SlidingWindowLimiter(limit=1, window_s=60, clock=lambda: 0.0)
    assert lim.hit("k") and not lim.hit("k")
    lim.reset("k")
    assert lim.hit("k")


def test_memory_is_bounded() -> None:
    lim = SlidingWindowLimiter(limit=1, window_s=60, clock=lambda: 0.0, max_keys=10)
    for i in range(100):
        lim.hit(str(i))
    assert lim.size() <= 10
