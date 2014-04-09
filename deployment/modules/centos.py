import functools

from fabric import colors
from fabric.api import cd, execute, path, run, settings, sudo, task

from utils import cget


INSTALL_PREFIX = '/usr/local'
GIT_VERSION = 'v1.9.1'
NODE_VERSION = 'v0.10.15'
PYTHON_VERSION = '2.7.6'
PYTHON_SUFFIX = PYTHON_VERSION[:-2]

SERVICES = {
    'cron': 'crond',
    'postgresql': 'postgresql-9.1',
}


def service(name, action):
    name = SERVICES.get(name, name)
    return sudo('/etc/init.d/{} {}'.format(name, action))


def yum_install(package):
    return sudo('yum -y install {}'.format(package))


def yum_group_install(group):
    return sudo('yum -y groupinstall {}'.format(group))


def check_command(command):
    '''Test if command exists and if not, execute the task.'''
    def wrapper(task):
        @functools.wraps(task)
        def wrapped(*args, **kwargs):
            with settings(warn_only=True):
                succeeded = run(command).succeeded
            if succeeded:
                print colors.green('Command "{}" succeeded. Skipping the '
                                   '"{}" task'
                                   .format(command, task.__name__))
            else:
                task(*args, **kwargs)
        return wrapped
    return wrapper


@task
def install_other_requirements():
    yum_install(' '.join([
        'java-1.6.0-openjdk',
        'libevent-devel',
    ]))


@task
def install_devel_requirements():
    yum_group_install('"Development Tools"')
    yum_install(' '.join([
        # Packages for Python.
        'zlib-devel',
        'bzip2-devel',
        'openssl-devel',
        'ncurses-devel',
        'sqlite-devel',
        'readline-devel',
        'tk-devel',
        'gdbm-devel',
        'db4-devel',
        'libpcap-devel',
        # Packages for Git.
        'curl-devel',
        'expat-devel',
        'gettext-devel',
        'openssl-devel',
    ]))


@task
@check_command('python{} -V'.format(PYTHON_SUFFIX))
def install_python():
    with cd('/tmp'):
        # Download, compile and install Python from sources.
        dirname = 'Python-{}'.format(PYTHON_VERSION)
        tarname = '{}.tgz'.format(dirname)
        run('curl -O https://www.python.org/ftp/python/{}/{}'.format(
            PYTHON_VERSION,
            tarname))
        run('tar xf {}'.format(tarname))
        with cd(dirname):
            run('./configure'
                ' --prefix={0}'
                ' --enable-unicode=ucs4'
                ' --enable-shared LDFLAGS="-Wl,-rpath {0}/lib"'
                .format(INSTALL_PREFIX))
            run('make')
            # Don't install as a main Python interpreter. It could break
            # system.
            sudo('make altinstall')


@task
@check_command('pip{} --version'.format(PYTHON_SUFFIX))
def install_pip():
    with cd('/tmp'):
        with path('{}/bin'.format(INSTALL_PREFIX)):
            run('curl -O https://bitbucket.org/pypa/setuptools/raw/bootstrap/'
                'ez_setup.py')
            sudo('python{} ez_setup.py --insecure'.format(PYTHON_SUFFIX))
            sudo('easy_install-{} pip'.format(PYTHON_SUFFIX))


@task
def install_python_requirements():
    with path('{}/bin:/usr/pgsql-9.1/bin'.format(INSTALL_PREFIX)):
        sudo('pip{} install virtualenv'.format(PYTHON_SUFFIX))
        sudo('pip{} install mercurial'.format(PYTHON_SUFFIX))
        sudo('pip{} install psycopg2'.format(PYTHON_SUFFIX))


@task
@check_command('git --version')
def install_git():
    version = cget('git_version', 'v1.9.1')
    with cd('/tmp'):
        dirname = 'git-{}'.format(version[1:])
        tarname = '{}.tar.gz'.format(version)
        run('wget -O {0} https://github.com/git/git/archive/{0}'
            .format(tarname))
        run('tar xf {}'.format(tarname))
        with cd(dirname):
            run('make configure')
            run('./configure --prefix={}'.format(INSTALL_PREFIX))
            run('make all')
            sudo('make install')


@task
def install_postgres():
    with cd('/tmp'):
        run('curl -O http://yum.postgresql.org/9.1/redhat/rhel-5-x86_64'
            '/pgdg-centos91-9.1-4.noarch.rpm')
        with settings(warn_only=True):
            sudo('rpm -ivh pgdg-centos91-9.1-4.noarch.rpm')
        yum_install(' '.join([
            'postgresql91-server',
            'postgresql91-devel',
        ]))
        # Initialize and start postgres.
        prefix = '/etc/init.d/postgresql-9.1'
        sudo('{} initdb'.format(prefix))
        sudo('{} start'.format(prefix))


@task
def install_nginx():
    sudo('''echo '[nginx]
name=nginx repo
baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
gpgcheck=0
enabled=1' > /etc/yum.repos.d/nginx.repo''')
    yum_install('nginx')


@task
@check_command('node -v && npm -v')
def install_node():
    with cd('/tmp'):
        dirname = 'node-{}'.format(NODE_VERSION)
        tarname = '{}.tar.gz'.format(dirname)
        run('curl -O http://nodejs.org/dist/{}/{}'.format(NODE_VERSION,
                                                          tarname))
        run('tar xf {}'.format(tarname))
        with cd(dirname):
            run('python{} configure'.format(PYTHON_SUFFIX))
            run('make')
            sudo('make install')


@task(default=True)
def install_requirements():
    execute(install_devel_requirements)
    execute(install_git)
    execute(install_python)
    execute(install_node)
    execute(install_postgres)
    execute(install_nginx)
    execute(install_pip)
    execute(install_python_requirements)
    execute(install_other_requirements)
