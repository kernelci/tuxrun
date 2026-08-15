# TuxRun outputs

TuxRun allows to record the outputs and results.

## Logs

By default, TuxRun will output the logs on the standard output. It's possible
to record the logs as `yaml` in a file with:

```shell
tuxrun --device qemu-armv5 --log-file-yaml logs.yaml
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
