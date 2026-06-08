"""Standalone runner entrypoint (`python -m devdash`). Fleshed out in M2."""


def main() -> None:
    print(f"devdash standalone runner (skeleton) — contract v{_contract()}")


def _contract() -> int:
    from devdash import CONTRACT_VERSION

    return CONTRACT_VERSION


if __name__ == "__main__":
    main()
