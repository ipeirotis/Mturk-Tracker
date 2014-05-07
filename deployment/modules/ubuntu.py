from os.path import join as pjoin

from fabric.api import settings, sudo, hide
from fabric.colors import yellow

from modules.utils import (PROPER_SUDO_PREFIX as SUDO_PREFIX, local_files_dir,
                           install_without_prompt, show, cget)


def service(name, action):
    return sudo("service %s %s" % (name, action))


def prep_apt_get():
    show(yellow("Updating and fixing apt-get."))
    with settings(sudo_prefix=SUDO_PREFIX, warn_only=False):
        with settings(hide("stdout", "running")):
            sudo("apt-get update")
        sudo("apt-get -f -y install")


def install_system_requirements():
    """Installs packages included in system_requirements.txt.
    This is done before fetch, thus the file is taken from *local* storage.

    """
    reqs = cget('system_requirements', [])
    for req in reqs:
        requirements = pjoin(local_files_dir("requirements"), req)
        show(yellow("Processing system requirements file: %s" %
                    requirements))
        with open(requirements) as f:
            r = ' '.join([f.strip() for f in f.readlines()])
            name = 'requirements: {0}'.format(r)
            with settings(sudo_prefix=SUDO_PREFIX):
                install_without_prompt(r, name, silent=False)


def install_nginx():
    """Add nginx repository to known repositories and installs it."""
    show(yellow("Installing nginx."))
    with settings(sudo_prefix=SUDO_PREFIX, warn_only=True):
        sudo("nginx=stable && add-apt-repository ppa:nginx/$nginx")
        sudo("apt-get update")
    install_without_prompt('nginx', 'nginx')


def install_virtualenv():
    """Installs virtualenv."""
    install_without_prompt('python-virtualenv', 'python virtual environment')


def install_requirements():
    prep_apt_get()
    install_system_requirements()
    install_virtualenv()
    install_nginx()
