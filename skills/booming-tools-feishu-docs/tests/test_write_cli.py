import pytest
import sys
from io import StringIO
from unittest.mock import patch, MagicMock, mock_open
from feishu_write import run

_MD = "# Hello\n\nWorld"
_URL = "https://boomingtech.feishu.cn/docx/docABC"


def test_from_file_prints_url(tmp_path, capsys):
    md_file = tmp_path / "doc.md"
    md_file.write_text(_MD, encoding="utf-8")
    with patch("feishu_write.get_token", return_value="tok"), \
         patch("feishu_write.create_document", return_value=_URL):
        run(["--title", "My Doc", str(md_file)])
    out = capsys.readouterr().out
    assert _URL in out
    assert "[OK]" in out


def test_from_stdin_prints_url(capsys):
    with patch("feishu_write.get_token", return_value="tok"), \
         patch("feishu_write.create_document", return_value=_URL), \
         patch("sys.stdin", StringIO(_MD)), \
         patch("sys.stdin.isatty", return_value=False):
        run(["--title", "Stdin Doc"])
    out = capsys.readouterr().out
    assert _URL in out


def test_missing_title_exits(capsys):
    with pytest.raises(SystemExit) as exc_info:
        run(["input.md"])
    assert exc_info.value.code != 0


def test_file_not_found_exits(capsys):
    with pytest.raises(SystemExit) as exc_info:
        run(["--title", "T", "nonexistent_file_xyz.md"])
    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "错误" in err


def test_tty_stdin_without_file_exits(capsys):
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = True
        with pytest.raises(SystemExit) as exc_info:
            run(["--title", "T"])
    assert exc_info.value.code != 0


def test_api_failure_exits(tmp_path, capsys):
    md_file = tmp_path / "doc.md"
    md_file.write_text(_MD, encoding="utf-8")
    with patch("feishu_write.get_token", return_value="tok"), \
         patch("feishu_write.create_document", side_effect=RuntimeError("创建失败")):
        with pytest.raises(SystemExit) as exc_info:
            run(["--title", "T", str(md_file)])
    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "错误" in err


def test_create_document_receives_correct_args(tmp_path):
    md_file = tmp_path / "doc.md"
    md_file.write_text("# Test", encoding="utf-8")
    with patch("feishu_write.get_token", return_value="mytoken"), \
         patch("feishu_write.create_document", return_value=_URL) as mock_create:
        run(["--title", "My Title", str(md_file)])
    args = mock_create.call_args
    assert args[0][0] == "My Title"
    assert isinstance(args[0][1], list)
    assert args[0][2] == "mytoken"


def test_partial_write_error_prints_url(tmp_path, capsys):
    from feishu.writer import PartialWriteError
    md_file = tmp_path / "doc.md"
    md_file.write_text(_MD, encoding="utf-8")
    partial_err = PartialWriteError("写入失败", url=_URL, n_written=50)
    with patch("feishu_write.get_token", return_value="tok"), \
         patch("feishu_write.create_document", side_effect=partial_err):
        with pytest.raises(SystemExit) as exc_info:
            run(["--title", "T", str(md_file)])
    assert exc_info.value.code != 0
    out = capsys.readouterr()
    combined = out.out + out.err
    assert _URL in combined


def test_permission_denied_hint(tmp_path, capsys):
    md_file = tmp_path / "doc.md"
    md_file.write_text(_MD, encoding="utf-8")
    with patch("feishu_write.get_token", return_value="tok"), \
         patch("feishu_write.create_document",
               side_effect=RuntimeError("创建文档失败（code=99991672）：Access denied")):
        with pytest.raises(SystemExit):
            run(["--title", "T", str(md_file)])
    err = capsys.readouterr().err
    assert "docx:document" in err
