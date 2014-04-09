import os
from os.path import join as pjoin

from pprint import pprint
from fabric import colors
from fabric.api import run, sudo, hide, settings, put, env, prefix, cd, abort
from fabric.contrib.files import upload_template
from fabric.contrib.console import confirm
from fabric import version as fversion


PROPER_SUDO_PREFIX = "sudo -i -S -p '%s' " \
                     if fversion.VERSION < (1, 4, 2) else \
                     "sudo -i -S -p '%(sudo_prompt)s' "


def confirm_or_abort(question="\nDo you want to continue?", default=False):
    if not confirm(colors.red(question), default=False):
        abort("Aborting deployment")


def show(msg, *args):
    """Print some message with increased visibility.
    If possible, message will be formatted using args. In case some arguments
    are missing, the exception will be caught and raw msg will be displayed.
    """
    try:
        msg = msg % args
    except TypeError:
        pass
    print colors.cyan('==>', bold=True), msg


def cget(name, default=None):
    u"Get configuration variable from the global context."
    return env["ctx"].get(name, default)


def cset(name, value, force=False):
    u"Save configuration variable to the global context, if it's not defined."
    if force:
        env["ctx"][name] = value
    else:
        value = env["ctx"].setdefault(name, value)
    return value


def print_context():
    show("Current configuration ")
    pprint(dict((k, v) for k, v in env["ctx"].items() if v is not None))
    show("Target: %s" % colors.green(env["host"]))
    show("Instance: %s" % colors.green(cget("instance")))
    show("Branch: %s" % colors.green(cget("branch") or "master"))
    tf = lambda x: colors.green(x) if x else colors.red(x)
    show("Requirements: %s" % tf(cget("requirements")))
    show("Setup environment: %s" % tf(cget("setup_environment")))


def local_files_dir(subpath=""):
    """Returns the absolute path of deployment assets (`files` directory).
    This is a *local* path. It is used before code fetch is done
    on the remote machine.
    """
    path = pjoin(cget("local_root"), "deployment", "files")
    if subpath:
        path = pjoin(path, subpath)
    return path


def remote_files_dir(subpath=""):
    """Returns the absolute path of deployment assets (`files` directory).
    This is a *remote* path. It is used after code fetch is done
    on the remote machine.
    """
    path = cget("deployment_files")
    if subpath:
        path = pjoin(path, subpath)
    return path


def get_permissions(path, use_sudo=False):
    command = use_sudo and sudo or run
    with settings(hide("running", "stdout")):
        result = command('stat --printf "%%a %%U %%G" %s' % path)
    mode, user, group = result.split()
    return mode, user, group


def ensure_permissions(path, mode=None, user=None, group=None, recursive=False):
    current = get_permissions(path, use_sudo=True)
    recursive = '--recursive' if recursive else ''
    if mode is not None and current[0] != mode:
        with settings(hide("running", "stdout")):
            sudo("chmod %s %s %s" % (recursive, str(mode), path))
    if user is not None and current[1] != user:
        with settings(hide("running", "stdout")):
            sudo("chown %s %s %s" % (recursive, user, path))
    if group is not None and current[2] != group:
        with settings(hide("running", "stdout")):
            sudo("chown %s :%s %s" % (recursive, group, path))


def put_file_with_perms(local, remote, mode=None, user=None, group=None):
    with settings(hide("running")):
        put(local, remote, use_sudo=True)
    ensure_permissions(remote, mode, user, group)


def create_dir_with_perms(path, mode=None, user=None, group=None):
    with settings(hide("running")):
        sudo("mkdir -p %s" % path)
    ensure_permissions(path, mode, user, group)


def upload_template_with_perms(source, destination, context=None, mode=None,
        user=None, group=None):
    try:
        with settings(hide("stdout", "running")):
            upload_template(source, destination, context=context, use_sudo=True,
                backup=False)
        ensure_permissions(destination, mode=mode, user=user, group=group)
    except TypeError as e:
        msg = "Error uploading settings file: {0}, to {1}: {2}"
        msg = msg.format(source, destination, str(e))
        show(colors.red(msg))
        show(colors.green("If it is a formatting error, you may want to search"
            " the uploaded settings file for any misintepreted %'s and replace"
            " them with: '%({0})s'.".format(cget('percent_escape_key'))))
        confirm_or_abort()


def upload_templated_folder_with_perms(source, source_root, destination_root,
    context=None, mode=None, directories_mode=None, user=None, group=None):
    """Walks the given source directory and copies all the files formatting
    them using upload_template_with_perms.
    """
    directories_mode = directories_mode or mode

    def __visit(arg, dirname, names):
        """os.path.walk 'visit' function."""
        # make sure the directory exists on target
        user = cget("user")
        dirpart = dirname[len(arg['root']) + 1:]
        target_dir = pjoin(arg['destination'], dirpart)
        create_target_directories([target_dir], directories_mode, user)
        for name in names:
            source = pjoin(dirname, name)
            destination = pjoin(target_dir, name)
            if not os.path.isdir(source):
                upload_template_with_perms(
                    source, destination, arg['context'], mode=arg["mode"],
                    group=arg['group'], user=arg['user'])
    arg = {
        'context': context,
        'mode': mode,
        'destination': destination_root,
        'root': source_root,
        'user': user,
        'group': group,
    }
    os.path.walk(source, __visit, arg)


def dir_exists(location):
    """Tells if there is a remote directory at the given location."""
    with settings(hide("running", "stdout")):
        res = run("test -d '%s' && echo OK ; true" % (location)).endswith("OK")
    return res


def run_django_cmd(command, args=""):
    ve_dir = cget("virtualenv_dir")
    show("Running django command: %s with args %s", command, args)
    with prefix('source %s' % pjoin(ve_dir, "bin", "activate")):
        with cd(cget("manage_py_dir")):
            with settings(hide("stdout", "running")):
                run("DJANGO_SETTINGS_MODULE=%s python manage.py %s %s" % (
                    cget("settings_full_name"), command, args))


def get_boolean(value):
        return bool(value in [True, 1, 'True', 'true', '1', 'T', 't'])


def install_without_prompt(packages, description, silent=True):
    """Installs given packages with no prompt and output.
    Parameters:
        packages - a string of space-separated package names.
    """
    show(colors.yellow("Installing {0}.").format(description))
    with settings(sudo_prefix=PROPER_SUDO_PREFIX):
        sudo("apt-get install -y{silent} {packages}".format(
            packages=packages, silent=' -q' if silent else ''))


def create_target_directories(dirs, perms, user):
    """Creates all directories in the list."""
    for name in dirs:
        if not dir_exists(name):
            show(colors.yellow("Creating missing directory: %s"), name)
            create_dir_with_perms(name, perms, user, user)
