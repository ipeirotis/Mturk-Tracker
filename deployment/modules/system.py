from fabric.api import abort
from fabric.colors import red

from . import centos, ubuntu
from utils import cget


MODULES = {'centos': centos, 'ubuntu': ubuntu}


def get_module():
    distro = cget('distro', 'ubuntu')
    if distro not in MODULES.keys():
        abort(red('Unknown distro: %s' % distro))
    return MODULES[distro]


def install_requirements():
    get_module().install_requirements()


def service(name, action):
    return get_module().service(name, action)
