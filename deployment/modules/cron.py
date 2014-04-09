from os.path import join as pjoin, isdir
from fabric.api import env, settings, hide
from fabric.colors import yellow, red
from modules.system import service
from modules.utils import (show, cget, create_target_directories,
        local_files_dir, upload_templated_folder_with_perms,
        upload_template_with_perms)


def configure():
    """Creates all neccessary folders and uploads settings.
    Keep in mind that the base for filenames is /etc, because the files reside
    in /etc/crond.d/ etc. Thus those files/folders must be specified explictly.

    Additionally this will format and upload
        manage_py_exec and
        manage_py_exec_silent

    scripts.

    """
    user = cget("user")
    logdir = pjoin(cget('log_dir'), 'cron')
    create_target_directories([logdir], "700", user)

    context = dict(env["ctx"])
    local_dir = local_files_dir("cron")
    dest_dir = "/etc"
    confs = cget("cron_files")

    show(yellow("Uploading cron configuration files: %s." % confs))
    if not confs or len(confs) == 0:
        show(red("No files to upload for cron."))
        return

    for name in confs:
        source = pjoin(local_dir, name)
        destination = pjoin(dest_dir, name)
        if isdir(source):
            upload_templated_folder_with_perms(source, local_dir, dest_dir,
                context, mode="644", user='root', group='root',
                directories_mode="700")
        else:
            upload_template_with_perms(
                source, destination, context, mode="644", user='root',
                group='root')

    # format and upload command execution script used by cron
    scripts = ['manage_py_exec', 'manage_py_exec_silent']
    for script_name in scripts:
        source = pjoin(cget("local_root"), 'deployment', 'scripts',
                script_name)
        destination = pjoin(cget("script_dir"), script_name)
        upload_template_with_perms(source, destination, context, mode="755")

    show(yellow("Reloading cron"))
    with settings(hide("stderr"), warn_only=True):
        res = service("cron", "reload")
        if res.return_code == 2:
            show(red("Error reloading cron!"))
