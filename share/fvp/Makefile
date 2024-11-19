LAVA_IMAGE ?= ""
RUNTIME ?= "podman"

aemva_version ?= "11.28_23"
ifeq ($(shell uname -m),aarch64)
aemva_version_sha256 ?= "a380e271f14ce7cf99158018368ac86fe8c305f82c7d332a93eb08bf7a172571"
aemva_arch = "Linux64_armv8l"
else
aemva_version_sha256 ?= "0f6d67d834a8ed5dff3c863e0e3545ef39c736405ea8227577ac004cffd66e93"
aemva_arch = "Linux64"
endif
morello_version ?= "0.11_34"
morello_version_sha256 ?= "ed1e110fb7fa8732d4f1bea9af69491a9e3f7dbf57d2ce6ea916d3cdf910d324"

container_aemva_version = $(shell echo $(aemva_version)|sed -e 's|_|.|g')
container_morello_version = $(shell echo $(morello_version)|sed -e 's|_|.|g')

.PHONE: build

build: fvp-aemva fvp-morello

fvp-aemva: aemva/Dockerfile
	cd aemva && $(RUNTIME) build --build-arg version=$(aemva_version) --build-arg version_sha256=$(aemva_version_sha256) --build-arg arch=$(aemva_arch) --tag fvp:aemva-$(container_aemva_version) .

fvp-morello: morello/Dockerfile
	cd morello && $(RUNTIME) build --build-arg version=$(morello_version) --build-arg version_sha256=$(morello_version_sha256) --tag fvp:morello-$(container_morello_version) .

clean:
	$(RUNTIME) image rm fvp:aemva-$(container_aemva_version) fvp:morello-$(container_morello_version)
