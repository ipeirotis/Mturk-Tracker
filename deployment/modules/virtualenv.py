from os.path import join as pjoin

from fabric.contrib.files import exists
from fabric.colors import yellow, green
from fabric.api import hide, settings, prefix, run
from utils import show, dir_exists, cget, remote_files_dir


def update_virtualenv():
    """Updates virtual Python environment."""
    ve_dir = cget("virtualenv_dir")
    activate = pjoin(ve_dir, "bin", "activate")
    cache = cget("pip_cache")

    show(yellow("Updating Python virtual environment."))
    show(green("Be patient. It may take a while."))

    for req in cget('pip_requirements'):
        requirements = pjoin(remote_files_dir('requirements'), req)
        show(yellow("Processing requirements file: %s" % requirements))
        with settings(warn_only=True):
            with prefix("source %s" % activate):
                run("pip install --no-input --download-cache=%s"
                    " --requirement %s --log=/tmp/pip.log" %
                    (cache, requirements))


def create_virtualenv():
    """Creates the virtualenv."""
    ve_dir = cget("virtualenv_dir")
    bin_path = pjoin(ve_dir, "bin")
    if not dir_exists(bin_path) or not exists(pjoin(bin_path, "activate")):
        show(yellow("Setting up new Virtualenv in: %s"), ve_dir)
        with settings(hide("stdout", "running")):
            run("virtualenv --distribute %s" % ve_dir)
