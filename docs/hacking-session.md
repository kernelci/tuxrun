# Hacking session

With a hacking session the user can connect to the device via tmate session.

```
tuxrun \
  --runtime podman \
  --device qemu-arm64 \
  --boot-args "rw" \
  --rootfs https://storage.tuxboot.com/debian/bookworm/arm64/rootfs.ext4.xz \
  --tests hacking-session \
  --parameters PUB_KEY="$(cat ~/.ssh/id_rsa.pub)"
```
Note: Make sure to have an SSH public key available at `~/.ssh/id_rsa.pub` or adjust path accordingly.

The output will look something like this:
```
2024-02-14T10:03:23 Connecting to ssh.tmate.io...
2024-02-14T10:03:24 ssh session read only: ssh ro-372tCdc5apCthA5jktKbzWbam@lon1.tmate.io
2024-02-14T10:03:24 ssh session: ssh NCjqLaJD8A9tBVr8u85uT4mu2@lon1.tmate.io
```

To connect would be to copy this into a new terminal:
```
ssh NCjqLaJD8A9tBVr8u85uT4mu2@lon1.tmate.io
```
