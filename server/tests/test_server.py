from server import hello


def test_truth():
    assert hello() == "Hello from server!"
