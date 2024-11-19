FROM docker.io/library/ubuntu:focal
ARG version
ARG version_sha256
ARG arch

ENV DEBIAN_FRONTEND=noninteractive
ENV PKG_DEPS="\
    bc \
    ca-certificates \
    curl \
    libatomic1 \
    libdbus-1-3 \
    openssh-server \
    telnet \
"

RUN if [ -z $version ]; then echo "FVP version not set!" && exit 1; fi
RUN set -ex ;\
    apt update -q=2 ;\
    apt full-upgrade -q=2 --yes ;\
    apt install --yes ca-certificates ;\
    apt install -q=2 --yes --no-install-recommends ${PKG_DEPS} ;\
    # Install the FVP model
    curl --connect-timeout 5 --retry 5 --retry-delay 1 -fsSLo /tmp/fvp.tgz \
    "https://developer.arm.com/-/cdn-downloads/permalink/FVPs-Architecture/FM-11.28/FVP_Base_RevC-2xAEMvA_${version}_${arch}.tgz" ;\
    echo "${version_sha256} /tmp/fvp.tgz" | sha256sum --check -;\
    tar xf /tmp/fvp.tgz -C /tmp ;\
    mkdir -p /opt/model/FVP_AEMvA/ ; \
    cp -R /tmp/Base_RevC_AEMvA_pkg/* /opt/model/FVP_AEMvA/ ;\
    # Make the AArch64 binaries look like x86-64 ones to tuxrun
    [ ! -e /opt/model/FVP_AEMvA/models/Linux64_GCC-9.3 ] && ln -s Linux64_armv8l_GCC-9.3 /opt/model/FVP_AEMvA/models/Linux64_GCC-9.3 ;\
    [ ! -e /opt/model/FVP_AEMvA/plugins/Linux64_GCC-9.3 ] && ln -s Linux64_armv8l_GCC-9.3 /opt/model/FVP_AEMvA/plugins/Linux64_GCC-9.3 ;\
    # Cleanup
    apt clean ;\
    rm -rf /var/lib/apt/lists/* /tmp/*
