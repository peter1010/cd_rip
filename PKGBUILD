pkgbase=cd_rip
pkgname=('cd_rip')
pkgver=1.0
pkgrel=6
pkgdesc="CD Ripper"
arch=('any')
url="http:"
license=('GPL')
makedepends=('python' 'python-build')
depends=('python' 'cdparanoia')
source=()

build() {
	pushd ..
	python -m build
	popd
}

pkgver() {
	pushd .. > /dev/null
	python version.py
	popd  > /dev/null
}

package() {
    pushd ..
	pip install dist/CD_Rip-$pkgver-py3-none-any.whl --force-reinstall --root="$pkgdir"
    popd
}

