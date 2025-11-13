LAVA_IMAGE ?= ""
RUNTIME ?= "podman"

morello_version ?= "0.11_34"
morello_version_sha256 ?= "ed1e110fb7fa8732d4f1bea9af69491a9e3f7dbf57d2ce6ea916d3cdf910d324"

container_morello_version = $(shell echo $(morello_version)|sed -e 's|_|.|g')

.PHONE: build

build: fvp-morello

fvp-morello: morello/Dockerfile
	cd morello && $(RUNTIME) build --build-arg version=$(morello_version) --build-arg version_sha256=$(morello_version_sha256) --tag fvp:morello-$(container_morello_version) .

clean:
	$(RUNTIME) image rm fvp:morello-$(container_morello_version)
