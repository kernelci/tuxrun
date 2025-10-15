# Installing TuxRun via Debian packages

TuxRun provides Debian packages that have minimal dependencies, and should
work on any Debian or Debian-based (Ubuntu, etc) system. TuxRun
depends on TuxLAVA, hence TuxLAVA repositories should be explicitly
added to install TuxRun.

1) Download the [repository signing
key](https://tuxlava.org/packages/signing-key.gpg) for TuxLAVA and
save it to `/etc/apt/trusted.gpg.d/tuxlava.gpg`, since TuxRun depends
on TuxLAVA.

```
sudo wget -O /etc/apt/trusted.gpg.d/tuxlava.gpg https://tuxlava.org/packages/signing-key.gpg
```

2) Create apt sources list for tuxlava packages:

```
echo "deb https://tuxlava.org/packages/ ./" | sudo tee /etc/apt/sources.list.d/tuxlava.list
```

3) Download the [repository signing
key](https://tuxrun.org/packages/signing-key.gpg) for TuxRun and save
it to `/etc/apt/trusted.gpg.d/tuxrun.gpg`.

```
sudo wget -O /etc/apt/trusted.gpg.d/tuxrun.gpg https://tuxrun.org/packages/signing-key.gpg
```

4) Create apt sources list for tuxrun packages:

```
echo "deb https://tuxrun.org/packages/ ./" | sudo tee /etc/apt/sources.list.d/tuxrun.list
```

5) Install `tuxrun` as you would any other package:

```
sudo apt update
sudo apt install tuxrun
```

Upgrading tuxrun will work just like it would for any other package (`apt
update`, `apt upgrade`).

## Install using Debian extrepo

extrepo is a tool that helps configuring external repositories on
Debian in a secure manner. As a pre-requisite for installation using
this method, extrepo should be installed in your Debian machine.

1) Install extrepo if it is not installed previously:

```
sudo apt update
sudo apt install extrepo
```

2) Enable the tuxrun and tuxlava repositories with extrepo, since
tuxrun depends on tuxlava:

```
sudo extrepo enable tuxlava
sudo extrepo enable tuxrun
```

3) Install tuxrun as you would any other package:

```
sudo apt update
sudo apt install tuxrun
```

If the URL or the GPG key has changed, once updated in the
extrepo-data repository, it can be easily updated with:

```
sudo extrepo update tuxrun
```
