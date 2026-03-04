from tuxrun.writer import Writer


def test_write_log_file(tmp_path):
    log_file = tmp_path / "logs"
    html_file = tmp_path / "logs.html"
    text_file = tmp_path / "logs.txt"
    yaml_file = tmp_path / "logs.yaml"
    with Writer(log_file, html_file, text_file, yaml_file) as writer:
        writer.write(
            '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}'
        )

    log_file.read_text(
        encoding="utf-8"
    ) == '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}\n'

    assert (
        html_file.read_text(encoding="utf-8")
        == """<!DOCTYPE html>
<html lang="en">
<head>
  <title>TuxTest log</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <style>
    body { background-color: black; color: white; }
    span.pass { color: green; }
    span.alert { color: red; }
    span.err { color: #FF7F7F; }
    span.debug { color: #FFFFFF; }
    span.info { color: #CCCCCC; }
    span.lavainfo { color: #B3BEE8; }
    span.warn { color: #FFA500; }
    span.timestamp { color: #AAFFAA; }
    span.feedback { color: orange; }
  </style>
</head>
<body>
<pre>
</pre>
</body>
</html>"""
    )
    assert text_file.read_text(encoding="utf-8") == ""


def test_write_stdout(capsys):
    with Writer("-", None, None, None) as writer:
        writer.write(
            '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}'
        )

    out, err = capsys.readouterr()
    assert "\x1b[0m \x1b[1;37mHello, world\x1b[0m\n" in out


def test_write_stdout_logs(capsys, tmp_path):
    html_file = tmp_path / "logs.html"
    text_file = tmp_path / "logs.txt"
    yaml_file = tmp_path / "logs.yaml"
    with Writer("-", html_file, text_file, yaml_file) as writer:
        writer.write(
            '{"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}'
        )

    out, err = capsys.readouterr()
    assert "\x1b[0m \x1b[1;37mHello, world\x1b[0m\n" in out

    assert (
        yaml_file.read_text(encoding="utf-8")
        == """- {"lvl": "info", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513"}\n"""
    )
    assert (
        html_file.read_text(encoding="utf-8")
        == """<!DOCTYPE html>
<html lang="en">
<head>
  <title>TuxTest log</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <style>
    body { background-color: black; color: white; }
    span.pass { color: green; }
    span.alert { color: red; }
    span.err { color: #FF7F7F; }
    span.debug { color: #FFFFFF; }
    span.info { color: #CCCCCC; }
    span.lavainfo { color: #B3BEE8; }
    span.warn { color: #FFA500; }
    span.timestamp { color: #AAFFAA; }
    span.feedback { color: orange; }
  </style>
</head>
<body>
<pre>
</pre>
</body>
</html>"""
    )
    assert text_file.read_text(encoding="utf-8") == ""


def test_write_stdout_feedback(capsys):
    with Writer("-", None, None, None) as writer:
        writer.write(
            '{"lvl": "feedback", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513", "ns": "testing"}'
        )

    out, err = capsys.readouterr()
    assert "\x1b[0m <\x1b[0;33mtesting\x1b[0m> \x1b[0;33mHello, world\x1b[0m\n" in out


def test_write_stdout_feedback_logs(capsys, tmp_path):
    html_file = tmp_path / "logs.html"
    text_file = tmp_path / "logs.txt"
    yaml_file = tmp_path / "logs.yaml"
    with Writer("-", html_file, text_file, yaml_file) as writer:
        writer.write(
            '{"lvl": "feedback", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513", "ns": "testing"}'
        )

    out, err = capsys.readouterr()
    assert "\x1b[0m <\x1b[0;33mtesting\x1b[0m> \x1b[0;33mHello, world\x1b[0m\n" in out

    assert (
        yaml_file.read_text(encoding="utf-8")
        == """- {"lvl": "feedback", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513", "ns": "testing"}\n"""
    )
    assert (
        html_file.read_text(encoding="utf-8")
        == """<!DOCTYPE html>
<html lang="en">
<head>
  <title>TuxTest log</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <style>
    body { background-color: black; color: white; }
    span.pass { color: green; }
    span.alert { color: red; }
    span.err { color: #FF7F7F; }
    span.debug { color: #FFFFFF; }
    span.info { color: #CCCCCC; }
    span.lavainfo { color: #B3BEE8; }
    span.warn { color: #FFA500; }
    span.timestamp { color: #AAFFAA; }
    span.feedback { color: orange; }
  </style>
</head>
<body>
<pre>
<span id="L0"><span class="timestamp">2021-04-08T18:42:25.139513</span> <span class="feedback">&lt;testing&gt; </span>Hello, world</span>
</pre>
</body>
</html>"""
    )
    assert text_file.read_text(encoding="utf-8") == "<testing> Hello, world\n"


def test_writer_invalid_yaml(capsys, tmpdir):
    data = '{"lvl": "feedback", "msg": "Hello, world", "dt": "2021-04-08T18:42:25.139513", "ns": "testing"}'
    with Writer(tmpdir / "logs", None, None, tmpdir / "logs.yaml") as writer:
        writer.write("{")
        writer.write("hello world")
        writer.write("{}")
        writer.write(data)
        writer.write("{hello: world}")
    out, err = capsys.readouterr()
    assert (
        out
        == """{
hello world
{}
{hello: world}
"""
    )
    assert err == ""
    assert (tmpdir / "logs").read_text(
        encoding="utf-8"
    ) == "\x1b[0;90m2021-04-08T18:42:25\x1b[0m <\x1b[0;33mtesting\x1b[0m> \x1b[0;33mHello, world\x1b[0m\n"
    assert (tmpdir / "logs.yaml").read_text(encoding="utf-8") == f"- {data}\n"
