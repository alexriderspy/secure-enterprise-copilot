from app.ratelimit import RateLimiter


def test_burst_then_refill():
    now = [0.0]
    rl = RateLimiter(per_minute=10, clock=lambda: now[0])
    assert [rl.allow("rohan")[0] for _ in range(11)] == [True] * 10 + [False]
    assert rl.allow("asha")[0]          # limits are per user
    now[0] = 6.0                        # 10 per minute = one every 6 seconds
    assert rl.allow("rohan")[0] and not rl.allow("rohan")[0]
