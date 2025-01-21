from ._core import hello_from_bin


def main() -> None:
    print("main")


def hello() -> str:
    return hello_from_bin()
