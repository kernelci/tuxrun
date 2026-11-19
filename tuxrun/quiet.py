# vim: set ts=4
#
# Copyright 2026-present Linaro Limited
#
# SPDX-License-Identifier: MIT

import ast
import re
import shlex
from typing import Any, Dict, List, Optional

from tuxrun.results import PATTERN

ROOT_START = re.compile(r"^start: (\d+) (\S+)(?: \(timeout (\S+)\))?")
ROOT_END = re.compile(r"^end: (\d+) (\S+) \(duration (\S+)\)")
SHOWN_INFO = re.compile(
    r"^(downloading |\d+ ?MB downloaded in |Fetching tests from |Untar tests from file )"
)
HOST_COMMAND = re.compile(r"^(?:Boot|Connect|Feedback) command: (.*)", re.DOTALL)
RETURNED = re.compile(r"^Returned (-?\d+) in (\d+) seconds")
PARSED_EXIT = re.compile(r"^Parsed command exited (zero|-?\d+)")
PARSED_FAIL = re.compile(
    r"^action: [^\n]*\ncommand: [^\n]*\nmessage: [^\n]*\n"
    r"output: (.*)\nreturn code: -?\d+$",
    re.DOTALL,
)
KEPT_LEVELS = ["target", "input", "feedback", "warning", "error", "exception"]


def names(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    return [
        item["name"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]


def describe(action: Any) -> Optional[str]:
    if not isinstance(action, dict) or len(action) != 1:
        return None
    kind, params = next(iter(action.items()))
    if not isinstance(params, dict):
        return None

    if kind == "deploy" and isinstance(params.get("to"), str):
        return f"Deploy to {params['to']}"
    if kind == "boot" and isinstance(params.get("method"), str):
        return f"Boot with {params['method']}"
    if kind == "test":
        tests = (
            names(params.get("definitions"))
            + names(params.get("interactive"))
            + names(params.get("monitors"))
        )
        if tests:
            return "Test " + ", ".join(tests)
    if kind == "command" and isinstance(params.get("name"), str):
        return f"Run command {params['name']}"
    return None


def describe_actions(job_definition: Any) -> Dict[str, str]:
    if not isinstance(job_definition, dict):
        return {}
    actions = job_definition.get("actions")
    if not isinstance(actions, list):
        return {}
    descriptions = {}
    for index, action in enumerate(actions, start=1):
        description = describe(action)
        if description is not None:
            descriptions[str(index)] = description
    return descriptions


def shell_command(text: str) -> str:
    try:
        if text.startswith("["):
            args = ast.literal_eval(text)
        else:
            args = shlex.split(text)
    except (ValueError, SyntaxError, TypeError, RecursionError):
        return text
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        return text
    return shlex.join(args)


def result_text(result: Dict[Any, Any]) -> str:
    definition = PATTERN.sub("", str(result.get("definition", "?")))
    case = PATTERN.sub("", str(result.get("case", "?")))
    text = f"{definition}.{case}: {result.get('result', '?')}"
    if "measurement" in result:
        measure = str(result["measurement"])
        if result.get("units"):
            measure += f" {result['units']}"
        text += f" ({measure})"
    return text


def line(data: Dict[str, Any], level: str, msg: str) -> Dict[str, Any]:
    return {"dt": data["dt"], "lvl": level, "msg": msg}


class Quiet:
    def __init__(self, job_definition: Any) -> None:
        self.descriptions = describe_actions(job_definition)
        self.previous_debug: Optional[str] = None

    def __call__(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        previous_debug = self.previous_debug
        self.previous_debug = None
        level = data["lvl"]
        msg = data["msg"]

        if level in KEPT_LEVELS:
            return data if isinstance(msg, str) else {**data, "msg": str(msg)}
        if level == "results":
            return self.result(data, msg)
        if not isinstance(msg, str):
            return None
        if level in ["info", "debug"] and (match := HOST_COMMAND.match(msg)):
            return line(data, "debug", f"$ {match.group(1)}")
        if level == "info":
            return self.info(data, msg, previous_debug)
        if level == "debug":
            return self.debug(data, msg, previous_debug)
        return None

    def command(
        self, data: Dict[str, Any], msg: str, previous_debug: Optional[str]
    ) -> Dict[str, Any]:
        if previous_debug is None:
            return line(data, "debug", msg)
        if not msg:
            return line(data, "debug", f"$ {previous_debug}")
        return line(data, "debug", f"$ {previous_debug}\n{msg}")

    def result(self, data: Dict[str, Any], msg: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(msg, dict):
            return None
        level = "error" if msg.get("result") == "fail" else "results"
        return line(data, level, result_text(msg))

    def info(
        self, data: Dict[str, Any], msg: str, previous_debug: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        if match := ROOT_START.match(msg):
            index, name, timeout = match.groups()
            return line(data, "info", self.action_start(index, name, timeout))
        if match := ROOT_END.match(msg):
            name, duration = match.group(2, 3)
            return line(data, "info", f"End of {name} (duration {duration})")
        if SHOWN_INFO.match(msg):
            return line(data, "info", msg)
        if match := PARSED_EXIT.match(msg):
            code = "0" if match.group(1) == "zero" else match.group(1)
            return self.command(data, f"Exit code {code}", previous_debug)
        if match := PARSED_FAIL.match(msg):
            return line(data, "debug", match.group(1))
        return None

    def action_start(self, index: str, name: str, timeout: Optional[str]) -> str:
        description = self.descriptions.get(index)
        details = []
        if description is None:
            description = f"Start {name}"
        else:
            details.append(name)
        if timeout is not None:
            details.append(f"timeout {timeout}")
        if not details:
            return description
        return f"{description} ({', '.join(details)})"

    def debug(
        self, data: Dict[str, Any], msg: str, previous_debug: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        if msg.startswith("Calling: "):
            command = shell_command(msg.removeprefix("Calling: "))
            return line(data, "debug", f"$ {command}")
        if msg.startswith(">> "):
            return line(data, "debug", msg.removeprefix(">> ").rstrip())
        if match := RETURNED.match(msg):
            code, seconds = match.groups()
            return line(data, "debug", f"Exit code {code} ({seconds} s)")
        if msg.startswith("output: "):
            output = msg.removeprefix("output: ")
            if previous_debug is None:
                return line(data, "debug", output)
            return self.command(data, output, previous_debug)
        self.previous_debug = msg
        return None
