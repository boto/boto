import os, sys, time, traceback
import StringIO
import smtplib
from boto.utils import ShellCommand
from boto.pyami.config import Config

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

class ScriptBase:

    @classmethod
    def GetConfig(cls):
        """
        Returns a Config object holding instance and user metadata for this server.
        """
        return Config()

    def __init__(self, config=None):
        self.log_fp = StringIO.StringIO()
        if config == None:
            self.config = self.GetConfig()
        self.instance_id = self.config.get_instance('instance-id', 'default')
        self.ts = self.get_ts()

    def get_ts(self):
        return time.strftime(ISO8601, time.gmtime())
        
    def notify(self, subject):
        to_string = self.config.get_user('notify_to', None)
        if to_string:
            try:
                from_string = self.config.get_user('notify_from', 'boto')
                body = "From: %s\n" % from_string
                body += "To: %s\n" % to_string
                body += "Subject: %s\n\n" % subject
                body += self.log_fp.getvalue()
                smtp_host = self.config.get_user('smtp_host', 'localhost')
                server = smtplib.SMTP(smtp_host)
                smtp_user = self.config.get_user('smtp_user', '')
                smtp_pass = self.config.get_user('smtp_pass', '')
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_string, to_string, body)
                server.quit()
            except:
                self.log_fp.write('\nnotify failed\n')

    def dump_instance_data(self):
        self.log_fp.write('Instance and Userdata...\n')
        self.config.dump_safe(self.log_fp)
        self.log_fp.write('\n')

    def mkdir(self, path):
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except:
                self.notify('Error creating directory: %s' % path)
                sys.exit(-1)

    def umount(self, path):
        if os.path.ismount(path):
            self.run('umount %s' % path)

    def run(self, command, check_err=True):
        self.last_command = ShellCommand(command, self.log_fp)
        if self.last_command.status != 0 and check_err:
            self.notify('Error encountered')
            sys.exit(-1)

    def main(self):
        pass
        
