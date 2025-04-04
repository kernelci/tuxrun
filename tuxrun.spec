Name:      tuxrun
Version:   1.2.0
Release:   0%{?dist}
Summary:   command line tool for testing Linux with curated test suites
License:   MIT
URL:       https://tuxrun.org/
Source0:   %{pypi_source}


BuildRequires: git
BuildRequires: make
BuildRequires: python3-devel
BuildRequires: python3-flit
BuildRequires: python3-pip
BuildRequires: python3-pytest
BuildRequires: python3-pytest-cov
BuildRequires: python3-pytest-mock
BuildRequires: python3-yaml
BuildRequires: python3-ruamel-yaml
BuildRequires: python3-jinja2
BuildRequires: python3-requests
BuildRequires: tuxlava
Requires: python3-yaml
Requires: python3-ruamel-yaml
Requires: python3-jinja2
Requires: python3-requests
Requires: tuxlava

BuildArch: noarch

Requires: python3 >= 3.6

%global debug_package %{nil}

%description
TuxRun, is a command line tool for testing Linux on QEMU or FVP, using curated
test suites.  TuxRun is a part of TuxSuite, a suite of tools and services to
help with Linux kernel development.

%prep
%setup -q

%build
export FLIT_NO_NETWORK=1
make run
#make man
#make bash_completion

%check
python3 -m pytest test/

%install
mkdir -p %{buildroot}/usr/share/%{name}/
cp -r run %{name} %{buildroot}/usr/share/%{name}/
mkdir -p %{buildroot}/usr/bin
ln -sf ../share/%{name}/run %{buildroot}/usr/bin/%{name}
#mkdir -p %{buildroot}%{_mandir}/man1
#install -m 644 %{name}.1 %{buildroot}%{_mandir}/man1/
#mkdir -p %{buildroot}/usr/share/bash-completion/completions/
#install -m 644 bash_completion/%{name} %{buildroot}/usr/share/bash-completion/completions/

%files
/usr/share/%{name}
%{_bindir}/%{name}
#%{_mandir}/man1/%{name}.1*
#/usr/share/bash-completion/completions/%{name}

%doc README.md
%license LICENSE

%changelog

* Mon Oct 11 2021 Antonio Terceiro <antonio.terceiro@linaro.org> - 0.11.0-1
- Initial version of the package
