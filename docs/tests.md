# Tests

TuxRun support some tests, each tests is supported on some but not all architectures.

> Tip: "Listing tests"
    You can list the supported tests with:
    ```shell
    tuxrun --list-tests
    ```

## Your own tests

`--test-yaml` pastes the LAVA test action in a file or a URL into the job. It
can be given several times. tuxlava needs to support it.

```shell
tuxrun --device qemu-arm64 --test-yaml oeqa.yaml
```

The file must have one test action with one test definition, and the definition
must have the same name as the file without `.yaml`. tuxrun looks for the
results under that name, and it exits with 2 when there are none.

## FVP AEMvA device

The following tests are supported by the default root filesystem.

Device    | Tests                                                                      | Parameters                                               |
----------|----------------------------------------------------------------------------|----------------------------------------------------------|
fvp-aemva | command                                                                    |                                                          |
fvp-aemva | kselftest-(arm64, gpio, ipc, ir, kcmp, kexec, *...)                        | COUPOWER, KSELFTEST, SKIPFILE, SHARD_NUMBER, SHARD_INDEX |
fvp-aemva | kunit\*                                                                    | KUNIT_TEST_MODULE                                        |
fvp-aemva | kvm-unit-tests                                                             |                                                          |
fvp-aemva | ltp-(fcntl-locktests, fs_bind, fs_perms_simple, fsx, nptl, smoke)          | SKIPFILE, SHARD_NUMBER, SHARD_INDEX                      |
fvp-aemva | modules                                                                    | MODULES_LIST, MODULES_SUBDIRS, MODULE_MODPROBE_NUMBER, SKIPLIST, SHARD_NUMBER, SHARD_INDEX |
fvp-aemva | perf                                                                       | PERF                                                     |
fvp-aemva | rcutorture                                                                 |                                                          |
fvp-aemva | systemd-analyze                                                            |                                                          |
fvp-aemva | v4l2                                                                       |                                                          |

The following tests are not supported by the default root filesystem. You should
provide a custom root filesystem.

Device    | Tests                                                                                                                                                 | Parameters                          |
----------|-------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
fvp-aemva | kselftest-(net, mm, *...)                                                                                                                             | COUPOWER, KSELFTEST, SKIPFILE, SHARD_NUMBER, SHARD_INDEX |
fvp-aemva | libgpiod                                                                                                                                              |                                                          |
fvp-aemva | libhugetlbfs                                                                                                                                          |                                                          |
fvp-aemva | ltp-(cap_bounds, commands, containers, controllers, crypto, cve, filecaps, fs, hugetlb, io, ipc, math, mm, pty, sched, securebits, syscalls, tracing) | SKIPFILE, SHARD_NUMBER, SHARD_INDEX                      |
fvp-aemva | vdso                                                                                                                                                  |                                                          |
fvp-aemva | mmtests-(db-sqlite-insert-small, hpc-scimarkc-small, io-blogbench, io-fio-randread-async-randwrite, io-fio-randread-async-seqwrite, io-fio-randread-sync-heavywrite, io-fio-randread-sync-randwrite, io-fsmark-small-file-stream, memdb-redis-benchmark-small, memdb-redis-memtier-small, scheduler-schbench, scheduler-sysbench-cpu, scheduler-sysbench-thread, workload-aim9-disk, workload-coremark, workload-cyclictest-fine-hackbench, workload-cyclictest-hackbench, workload-ebizzy, workload-pmqtest-hackbench, workload-stressng-af-alg, workload-stressng-bad-altstack, workload-stressng-class-io-parallel, workload-stressng-context, workload-stressng-get, workload-stressng-getdent, workload-stressng-madvise, workload-stressng-mmap, workload-stressng-vm-splice, workload-stressng-zombie, workload-usemem, workload-will-it-scale-io-processes, workload-will-it-scale-io-threads, workload-will-it-scale-pf-processes, workload-will-it-scale-pf-threads, workload-will-it-scale-sys-processes, workload-will-it-scale-sys-threads) | ITERATIONS, MMTESTS_PATH, FULL_ARCHIVE                   |
fvp-aemva | xfstests-(btrfs, ext4, f2fs, Nilfs2, xfs)                                                                                                             |                                                          |

> Tip: "Passing parameters"
    In order to pass parameters for kselftest or perf, use
    `tuxrun --parameters KSELFTEST=http://.../kselftest.tar.xz` or
    `tuxrun --parameters PERF=http://.../perf.tar.xz`

> Info: "kselftest parameters"
    The `CPUPOWER` and `KSELFTEST` parameters are not mandatory. If kselftest
    is present on the filesystem (in `/opt/kselftests/default-in-kernel/`) then the
    parameter is not required.

> Info: "Running a commands"
    When running a commands test passing a `--parameters command-name=custom-test-name`

> Info: "ltp parameter"
    The `SKIPFILE` parameter is not mandatory but allows to specify a skipfile
    present on the root filesystem.

> Info: "kselftest and ltp sharding"
    In order to run kselftest and/or ltp with sharding, define `SHARD_NUMBER`
    to the number of shards and `SHARD_INDEX` to the shard to run. The list of
    kselftest or ltp tests will be sharded by`SHARD_NUMBER` and only the
    `SHARD_INDEX` part will be ran.

> Warning: "KUnit config"
    In order to run KUnit tests, the kernel should be compiled with
    ```
    CONFIG_KUNIT=m
    CONFIG_KUNIT_ALL_TESTS=m
    ```
    The **modules.tar.xz** should be given with `--modules https://.../modules.tar.xz`.


## FVP Morello devices

Device              | Tests          | Parameters                       |
--------------------|----------------|----------------------------------|
fvp-morello-android | binder         |                                  |
fvp-morello-android | bionic         | GTEST_FILTER\* BIONIC_TEST_TYPE\*|
fvp-morello-android | boottest       |                                  |
fvp-morello-android | boringssl      | SYSTEM_URL                       |
fvp-morello-android | compartment    | USERDATA                         |
fvp-morello-android | device-tree    |                                  |
fvp-morello-android | dvfs           |                                  |
fvp-morello-android | libjpeg-turbo  | LIBJPEG_TURBO_URL, SYSTEM_URL    |
fvp-morello-android | libpdfium      | PDFIUM_URL, SYSTEM_URL           |
fvp-morello-android | libpng         | PNG_URL, SYSTEM_URL              |
fvp-morello-android | lldb           | LLDB_URL, TC_URL                 |
fvp-morello-android | logd           | USERDATA                         |
fvp-morello-android | libpcre        |                                  |
fvp-morello-android | multicore      |                                  |
fvp-morello-android | smc91x         |                                  |
fvp-morello-android | virtio_net     |                                  |
fvp-morello-android | zlib           | SYSTEM_URL                       |
fvp-morello-busybox | purecap        |                                  |
fvp-morello-busybox | smc91x         |                                  |
fvp-morello-busybox | virtio_net     |                                  |
fvp-morello-busybox | virtiop9       |                                  |
fvp-morello-debian  | debian-purecap |                                  |
fvp-morello-oe      | fwts           |                                  |

> Tip: "Passing parameters"
    In order to pass parameters, use `tuxrun --parameters USERDATA=http://.../userdata.tar.xz`

> Tip: "Default parameters"
    **GTEST_FILTER** is optional and defaults to
    ```
    string_nofortify.*-string_nofortify.strlcat_overread:string_nofortify.bcopy:string_nofortify.memmove
    ```
    **BIONIC_TEST_TYPE** is optional and defaults to `static`. Valid values are `dynamic` and `static`.


## FVP LAVA device

The 'fvp-lava' device type has been specifically added to allow users to execute a FVP [LAVA](https://lava.readthedocs.io/en/latest/) Job definition locally using TuxRun. This device type will not ignore any test cases passed from cli and execute all the tests which are in the LAVA Job definition

## QEMU devices

The following tests are supported by the default root filesystem.

Device  | Tests                                                                      | Parameters                                               |
--------|----------------------------------------------------------------------------|----------------------------------------------------------|
qemu-\* | command                                                                    |                                                          |
qemu-\* | kselftest-(arm64, gpio, ipc, ir, kcmp, kexec, *...)                        | CPUPOWER, KSELFTEST, SKIPFILE, SHARD_NUMBER, SHARD_INDEX |
qemu-\* | kunit\*                                                                    | KUNIT_TEST_MODULE                                        |
qemu-\* | kvm-unit-tests                                                             |                                                          |
qemu-\* | ltp-(fcntl-locktests, fs_bind, fs_perms_simple, fsx, nptl, smoke)          | SKIPFILE, SHARD_NUMBER, SHARD_INDEX                      |
qemu-\* | modules                                                                    | MODULES_LIST, MODULES_SUBDIRS, MODULE_MODPROBE_NUMBER, SKIPLIST, SHARD_NUMBER, SHARD_INDEX |
qemu-\* | perf                                                                       | PERF                                                     |
qemu-\* | rcutorture                                                                 |                                                          |
qemu-\* | systemd-analyze                                                            |                                                          |
qemu-arm64 | tfa-tests                                                               |                                                          |
qemu-\* | v4l2                                                                       |                                                          |

The following tests are not supported by the default root filesystem. You should
provide a custom root filesystem.

Device  | Tests                                                                                                                                                 | Parameters                             |
--------|-------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------|
qemu-\* | kselftest-(net, mm, *...)                                                                                                                             | CPUPOWER, KSELFTEST, SKIPFILE, SHARD_NUMBER, SHARD_INDEX |
qemu-\* | libgpiod                                                                                                                                              |                                                          |
qemu-\* | libhugetlbfs                                                                                                                                          |                                                          |
qemu-\* | ltp-(cap_bounds, commands, containers, controllers, crypto, cve, filecaps, fs, hugetlb, io, ipc, math, mm, pty, sched, securebits, syscalls, tracing) | SKIPFILE, SHARD_NUMBER, SHARD_INDEX                      |
qemu-\* | vdso                                                                                                                                                  |                                                          |
qemu-\* | mmtests-(db-sqlite-insert-small, hpc-scimarkc-small, io-blogbench, io-fio-randread-async-randwrite, io-fio-randread-async-seqwrite, io-fio-randread-sync-heavywrite, io-fio-randread-sync-randwrite, io-fsmark-small-file-stream, memdb-redis-benchmark-small, memdb-redis-memtier-small, scheduler-schbench, scheduler-sysbench-cpu, scheduler-sysbench-thread, workload-aim9-disk, workload-coremark, workload-cyclictest-fine-hackbench, workload-cyclictest-hackbench, workload-ebizzy, workload-pmqtest-hackbench, workload-stressng-af-alg, workload-stressng-bad-altstack, workload-stressng-class-io-parallel, workload-stressng-context, workload-stressng-get, workload-stressng-getdent, workload-stressng-madvise, workload-stressng-mmap, workload-stressng-vm-splice, workload-stressng-zombie, workload-usemem, workload-will-it-scale-io-processes, workload-will-it-scale-io-threads, workload-will-it-scale-pf-processes, workload-will-it-scale-pf-threads, workload-will-it-scale-sys-processes, workload-will-it-scale-sys-threads)                                                                                     | ITERATIONS, MMTESTS_PATH, FULL_ARCHIVE                   |
qemu-\* | xfstests-(btrfs, ext4, f2fs, Nilfs2, xfs)                                                                                                             |                                                          |

> Tip: "Passing parameters"
    In order to pass parameters for kselftest or perf, use
    `tuxrun --parameters KSELFTEST=http://.../kselftest.tar.xz` or
    `tuxrun --parameters PERF=http://.../perf.tar.xz`

> Info: "kselftest parameters"
    The `CPUPOWER` and `KSELFTEST` parameters are not mandatory. If kselftest
    is present on the filesystem (in `/opt/kselftests/default-in-kernel/`) then the
    parameter is not required.

> Info: "Running a commands"
    When running a commands test passing a `--parameters command-name=custom-test-name`

> Info: "ltp parameter"
    The `SKIPFILE` parameter is not mandatory but allows to specify a skipfile
    present on the root filesystem.

> Info: "kselftest and ltp sharding"
    In order to run kselftest and/or ltp with sharding, define `SHARD_NUMBER`
    to the number of shards and `SHARD_INDEX` to the shard to run. The list of
    kselftest or ltp tests will be sharded by`SHARD_NUMBER` and only the
    `SHARD_INDEX` part will be ran.

> Info: "kselftest-arm64"
    Kselftest-arm64 are tests that can run on a qemu-arm64 machine.

> Warning: "KUnit config"
    In order to run KUnit tests, the kernel should be compiled with
    ```
    CONFIG_KUNIT=m
    CONFIG_KUNIT_ALL_TESTS=m
    ```
    The **modules.tar.xz** should be given with `--modules https://.../modules.tar.xz`.
