# vim: set ts=4
#
# Copyright 2021-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import html
import logging
import re
import sys
from contextlib import ContextDecorator

import yaml

from tuxrun.yaml import yaml_load

COLORS = {
    "exception": "\033[1;31m",
    "error": "\033[1;31m",
    "warning": "\033[1;33m",
    "info": "\033[1;37m",
    "debug": "\033[0;37m",
    "target": "\033[32m",
    "input": "\033[0;35m",
    "feedback": "\033[0;33m",
    "results": "\033[1;34m",
    "dt": "\033[0;90m",
    "end": "\033[0m",
}
LOG = logging.getLogger("tuxrun")

HTML_HEADER = """<!DOCTYPE html>
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
"""

HTML_FOOTER = """</pre>
</body>
</html>"""


class Writer(ContextDecorator):
    def __init__(self, log_file, html_file, text_file, yaml_file, quiet=None):
        self.log_file = log_file
        self.quiet = quiet
        self.html_file = html_file
        self.text_file = text_file
        self.yaml_file = yaml_file

        self.lineno = 0
        self.kernel_level_pattern = re.compile(r"^\<([0-7])\>")
        self.kernel_log_levels = {
            "0": "alert",
            "1": "alert",
            "2": "alert",
            "3": "err",
            "4": "warn",
            "5": "info",
            "6": "info",
            "7": "debug",
        }

    def __enter__(self):
        def fopen(p):
            if str(p) == "-":
                return sys.stdout
            return p.open("w")

        if self.log_file is not None:
            self.log_file = fopen(self.log_file)
        if self.html_file is not None:
            self.html_file = fopen(self.html_file)
            self.html_file.write(HTML_HEADER)
        if self.text_file is not None:
            self.text_file = fopen(self.text_file)
        if self.yaml_file is not None:
            self.yaml_file = fopen(self.yaml_file)
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        def fclose(f):
            if f is not None and f != sys.stdout:
                f.close()

        if self.html_file is not None:
            self.html_file.write(HTML_FOOTER)
        fclose(self.log_file)
        fclose(self.text_file)
        fclose(self.html_file)
        fclose(self.yaml_file)

    def write(self, line):
        line = line.rstrip("\n")
        try:
            data = yaml_load(line)
        except yaml.YAMLError:
            sys.stdout.write(line + "\n")
            return
        if not data or not isinstance(data, dict):
            sys.stdout.write(line + "\n")
            return
        if not {"dt", "lvl", "msg"}.issubset(data.keys()):
            sys.stdout.write(line + "\n")
            return

        log = self.quiet(data) if self.quiet else data
        if self.log_file is not None and log is not None:
            level = log["lvl"]
            msg = log["msg"]
            ns = " "
            if level == "feedback" and "ns" in log:
                ns = f" <{COLORS['feedback']}{log['ns']}{COLORS['end']}> "
            timestamp = log["dt"].split(".")[0]

            if msg and level == "input" and msg[-1] == "\n":
                msg = msg[0:-1] + "⏎"
            self.log_file.write(
                f"{COLORS['dt']}{timestamp}{COLORS['end']}{ns}{COLORS[level]}{msg}{COLORS['end']}\n"
            )

        if self.yaml_file is not None:
            self.yaml_file.write("- " + line + "\n")

        if data["lvl"] in ["target", "feedback"]:
            if self.text_file is not None:
                if data["lvl"] == "feedback" and "ns" in data:
                    self.text_file.write(f"<{data['ns']}> ")
                self.text_file.write(data["msg"] + "\n")

            if self.html_file is not None:
                # Build the html output
                kernel_level = self.kernel_level_pattern.match(data["msg"])

                self.html_file.write(f"""<span id="L{self.lineno}">""")
                self.html_file.write(
                    f"""<span class="timestamp">{data['dt']}</span> """
                )
                if kernel_level:
                    cls = self.kernel_log_levels[kernel_level.group(1)]
                    self.html_file.write(
                        f"""<span class="{cls}">{html.escape(data["msg"])}</span>"""
                    )
                else:
                    ns = ""
                    if data["lvl"] == "feedback" and "ns" in data:
                        ns = f"<span class=\"feedback\">{html.escape('<' + data['ns'] + '> ')}</span>"
                    self.html_file.write(ns + html.escape(data["msg"]))
                self.html_file.write("</span>\n")
                self.lineno += 1
