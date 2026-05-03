from demo_app.calculator import add, multiply, subtract


def test_add() -> None:
    assert add(2, 3) == 5


def test_multiply() -> None:
    assert multiply(4, 5) == 20


def test_subtract() -> None:
    assert subtract(7, 2) == 5
