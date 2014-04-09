from os.path import join as pjoin, isdir
from fabric.api import sudo, settings, env, hide
from fabric.colors import yellow, red
from modules.system import service
from modules.utils import (PROPER_SUDO_PREFIX as SUDO_PREFIX, show, cget,
        create_target_directories, local_files_dir,
        upload_templated_folder_with_perms, upload_template_with_perms)


def configure():
    """Creates all neccessary folders and uploads settings."""
    user = cget("user")
    sdir = pjoin(cget('service_dir'), 'nginx')
    logdir = pjoin(cget('log_dir'), 'nginx')
    create_target_directories([sdir, logdir], "700", user)
    context = dict(env["ctx"])
    local_dir = local_files_dir("nginx")
    dest_dir = "/etc/nginx"
    confs = cget("nginx_files") or [local_dir]
    show(yellow("Uploading nginx configuration files: {}.".format(confs)))
    for name in confs:
        source = pjoin(local_dir, name)
        destination = pjoin(dest_dir, name)
        if isdir(source):
            upload_templated_folder_with_perms(source, local_dir, dest_dir,
                context, mode="644", directories_mode="700")
        else:
            upload_template_with_perms(
                source, destination, context, mode="644")
    enabled = cget("nginx_sites_enabled")
    with settings(hide("running", "stderr", "stdout"), sudo_prefix=SUDO_PREFIX,
            warn_only=True):
        show("Enabling sites: {}.".format(enabled))
        for s in enabled:
            available = '/etc/nginx/sites-available'
            enabled = '/etc/nginx/sites-enabled'
            ret = sudo("ln -s {available}/{site} {enabled}/{site}".format(
                available=available, enabled=enabled, site=s))
            if ret.failed:
                show(red("Error enabling site: {}: {}.".format(s, ret)))


def reload():
    """Starts or restarts nginx."""
    with settings(hide("stderr"), sudo_prefix=SUDO_PREFIX, warn_only=True):
        service("nginx", "reload")
        res = service("nginx", "restart")
        if res.return_code == 2:
            show(yellow("Nginx unavailable, starting new process."))
            res = service("nginx", "start")
            if res.return_code != 0:
                show(red("Error starting nginx!"))
