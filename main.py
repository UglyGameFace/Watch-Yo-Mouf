"""Discloud entry point for Watch Yo Mouf."""

from __future__ import annotations

import logging

from watch_yo_mouf.config import ConfigurationError, load_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        # ConfigurationError intentionally never contains token values.
        raise SystemExit(f"Watch Yo Mouf configuration error: {exc}") from None

    from watch_yo_mouf.gateway import create_bot

    bot = create_bot(settings)
    bot.run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
