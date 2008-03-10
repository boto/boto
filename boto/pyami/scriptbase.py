import os, sys, time, traceback
import smtplib
from boto.utils import ShellCommand, get_ts
import boto

class ScriptBase:

    def __init__(self):
        self.instance_id = boto.config.get_instance('instance-id', 'default')
        self.ts = get_ts()

    def notify(self, subject):
        to_string = boto.config.get_value('Notification', 'smtp_to', None)
        if to_string:
            try:
                from_string = boto.config.get_value('Notification', 'smtp_from', 'boto')
                body = "From: %s\n" % from_string
                body += "To: %s\n" % to_string
                body += "Subject: %s\n\n" % subject
                #body += self.log_fp.getvalue()
                smtp_host = boto.config.get_value('Notification', 'smtp_host', 'localhost')
                server = smtplib.SMTP(smtp_host)
                smtp_user = boto.config.get_value('Notification', 'smtp_user', '')
                smtp_pass = boto.config.get_value('Notification', 'smtp_pass', '')
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_string, to_string, body)
                server.quit()
            except:
                boto.log.error('notify failed')

    def mkdir(self, path):
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except:
                boto.log.error('Error creating directory: %s' % path)

    def umount(self, path):
        if os.path.ismount(path):
            self.run('umount %s' % path)

    def run(self, command, notify=False, exit_on_error=False):
        self.last_command = ShellCommand(command)
        if self.last_command.status != 0:
            if notify:
                self.notify('Error encountered')
            if exit_on_error:
                sys.exit(-1)

    def main(self):
        pass
        
