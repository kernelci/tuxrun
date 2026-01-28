pkgname=tuxrun
pkgver=1.4.0
pkgrel=1
pkgdesc='TuxRun is a command line tool for testing Linux with curated test suites'
url='https://tuxrun.org/'
license=('MIT')
arch=('any')
depends=('python' 'python-jinja' 'python-requests' 'python-yaml' 'python-ruamel-yaml' 'tuxlava')
makedepends=('git' 'python-build' 'python-flit' 'python-installer' 'python-wheel')
checkdepends=('python-pytest' 'python-pytest-cov' 'python-pytest-mock')
optdepends=('docker: Container-based build support'
            'podman: Container-based build support'
            'socat: Offline build support')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
  cd "$pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

check() {
  cd "$pkgname-$pkgver"
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" pytest
}

package() {
  cd "$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dvm644 LICENSE -t "$pkgdir/usr/share/licenses/$pkgname"
}
