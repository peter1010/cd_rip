pkgbase=cd_rip
pkgname=('cd_rip')
pkgver=1.0
pkgrel=2
pkgdesc="CD Ripper"
arch=('any')
url="http:"
license=('GPL')
makedepends=('python')
depends=('python' 'cdparanoia')
source=()

pkgver() {
    python ../setup.py -V
}

check() {
    pushd ..
    python setup.py check
    popd
}

package() {
    pushd ..
    python setup.py install --root=$pkgdir
    popd
}

