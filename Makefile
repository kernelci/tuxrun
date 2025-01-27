export PROJECT := tuxrun
export TUXPKG_MIN_COVERAGE := 85
export TUXPKG_FLAKE8_OPTIONS := --ignore=E203,E501,W503
check: typecheck test spellcheck stylecheck

include $(shell tuxpkg get-makefile)

.PHONY: tags

stylecheck: style flake8

spellcheck:
	codespell \
		-I codespell-ignore-list \
		--check-filenames \
		--skip '.git,public,dist,*.sw*,*.pyc,tags,*.json,.coverage,htmlcov,*.jinja2,*.yaml'

integration:
	python3 test/integration.py --devices "qemu-*" --tests ltp-smoke
	python3 test/integration.py --devices "fvp-aemva" --tests ltp-smoke

doc: docs/index.md
	mkdocs build

docs/index.md: README.md scripts/readme2index.sh
	scripts/readme2index.sh $@

doc-serve:
	mkdocs serve

flit = flit
publish-pypi:
	$(flit) publish

tags:
	ctags -R $(PROJECT)/ test/

release: integration


rpm-sanity-check-prepare::
	printf '[tuxlava]\nname=tuxlava\ntype=rpm-md\nbaseurl=https://tuxlava.org/packages/\ngpgcheck=1\ngpgkey=https://tuxlava.org/packages/repodata/repomd.xml.key\nenabled=1\n' > /etc/yum.repos.d/tuxlava.repo

deb-sanity-check-prepare::
	apt-get update
	apt-get install -qy ca-certificates
	/usr/lib/apt/apt-helper download-file https://tuxlava.org/packages/signing-key.gpg /etc/apt/trusted.gpg.d/tuxlava.gpg
	echo 'deb https://tuxlava.org/packages/ ./' > /etc/apt/sources.list.d/tuxlava.list
	echo 'deb http://deb.debian.org/debian bookworm contrib' > /etc/apt/sources.list.d/contrib.list
	apt-get update