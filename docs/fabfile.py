from fabric.operations import sudo, local, put

def deploy(**kwargs):
    remote_path = '/var/www'
    if kwargs.get('remote_path', None):
        remote_path = kwargs['remote_path']
    
    # Update
    local("svn up ../")
    rev = local("svn info | grep Revision")
    rev = rev.replace("Revision: ", "").strip()
    tmp_folder_name = 'boto-docs.r%s' % rev
    archive_name = '%s.tar.gz' % tmp_folder_name
    
    # Clean
    local("rm -rf %s" % tmp_folder_name)
    local("rm -f %s" % archive_name)
    
    # Build
    local("make html")
    local("mv build/html %s" % tmp_folder_name)
    local("tar zcf %s %s" % (archive_name, tmp_folder_name))
    
    # Deploy
    put(archive_name, '~/')
    sudo("rm -f %s/%s && mv ~/%s %s/%s" % (remote_path, archive_name, archive_name, remote_path, archive_name))
    sudo("cd %s && rm -rf %s && tar zxf %s" % (remote_path, tmp_folder_name, archive_name))
    sudo("cd %s && rm -f boto-docs && ln -s %s boto-docs" % (remote_path, tmp_folder_name))
    
    # Validate
    sudo("ls -al %s" % remote_path)