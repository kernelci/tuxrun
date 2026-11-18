# TuxRun outputs

TuxRun allows to record the outputs and results.

## Logs

By default, TuxRun will output the logs on the standard output. It's possible
to record the logs as `yaml` in a file with:

```shell
tuxrun --device qemu-armv5 --log-file-yaml logs.yaml
```

With `--quiet`, the log on the standard output or in `--log-file` only has the
job actions, the downloads, where the test definitions come from, the commands
that LAVA runs on the host with their output and exit code, the results, the
warnings and errors, what LAVA sends to the device, and the device output. The
commands are printed after a `$` and a failed result is printed in red. LAVA
logs some commands without shell quotes, so check the quotes before you copy
one into a shell:

```shell
tuxrun --device qemu-armv5 --quiet
```

TuxRun can also extract the device output and save the logs as either `html` or `text`:

```shell
tuxrun --device qemu-armv5 --log-file-html logs.html --log-file-text logs.txt
```

## Results

When running the tests, TuxRun is recording the results of each individual
tests. The file can be dumped on the file system as `json`:

```shell
tuxrun --device qemu-armv5 --results results.json
```

The results can also be saved as JUnit XML, for example for the test report
of a GitLab job:

```shell
tuxrun --device qemu-armv5 --results-junit junit.xml
```

With `-` the XML goes to the standard output.

A failed test case is a `failure`, a skipped one is `skipped` and any other
result is an `error`. A test that was asked for but has no results, like when
the board doesn't boot, is an `error` too. JUnit has no field for a
measurement, so it goes into `system-out`. The `system-out` of a test case also
has the board output between its STARTTC and ENDTC (`lava-test-case --shell` or
`--output`), or else only its signal line, if it has one.

## Outputs

TuxRun can collect and dump to the filesystem every outputs with:

```shell
tuxrun --device qemu-mips32 --save-outputs
```

Every outputs will be saved into `~/.cache/tuxrun/tests/<test-id>/`.

You can override specific file path with the corresponding option. To record outputs and keep printing logs to stdout:

```shell
tuxrun --device qemu-mips32 --save-outputs --log-file -
```

Save output into another directory use `--cache-dir /abs/or/rel/path/to/output/dir`.
The output will be stored in `/abs/or/rel/path/to/output/dir/tests/<test-id>/`.

```shell
tuxrun --device qemu-mips32 --save-outputs --cache-dir /abs/or/rel/path/to/output/dir --log-file -
```

## Reproducer

The output directory also contains `reproducer.sh`, the command line that was
used. The file is executable, so it runs directly:

```shell
~/.cache/tuxrun/tests/1/reproducer.sh
```

It is written before the test starts, so it is there also when the test fails.

Values given with `--secrets` are masked, so no token is written to the output
directory. Put them back before running the script.
