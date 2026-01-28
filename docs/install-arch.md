# Installing TuxRun via Arch Linux packages

TuxRun provides Arch Linux packages that have minimal dependencies.

1. Create /etc/pacman.d/tuxlava.conf with the following contents:

```
[tuxlava]
SigLevel = Optional TrustAll
Server = https://tuxlava.org/packages/
```

2. Create /etc/pacman.d/tuxrun.conf with the following contents:

```
[tuxrun]
SigLevel = Optional TrustAll
Server = https://tuxrun.org/packages/
```

3. Include it from /etc/pacman.conf. Add one line at the bottom:

```
Include = /etc/pacman.d/*.conf
```

If you already have this line, do nothing.

4. Sync and install:

```shell
# pacman -Syu
# pacman -S tuxrun
```

Upgrades will be available in the same repository.

### Method 2: Manual download and install

If the pacman database is not available, download and install manually:

```shell
# curl -LO https://tuxrun.org/packages/tuxrun-VERSION-any.pkg.tar.zst
# pacman -U tuxrun-VERSION-any.pkg.tar.zst
```

Replace VERSION with the desired version number.
