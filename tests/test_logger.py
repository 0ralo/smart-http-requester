import logging

from services.logger import setup_logger


def test_setup_logger_writes_messages_to_file(tmp_path):
    log_dir = tmp_path / "logs"
    log_file = log_dir / "app.log"

    logger = setup_logger(
        name="test_logger",
        log_dir=log_dir,
        log_file=log_file,
        level=logging.INFO,
    )
    logger.info("hello from test logger")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "hello from test logger" in content
    assert "INFO" in content
