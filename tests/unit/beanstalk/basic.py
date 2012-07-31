import unittest
#import mock
import random
import os
import tempfile
import time
from boto.beanstalk.beanstalk import Beanstalk
from boto.beanstalk.response import Wrapper as response


class BasicSuite(unittest.TestCase):

    # file in python temp dir to store data to persist between test runs
    tmp_file_name = 'unittest_boto_beanstalk_rand.tmp'

    # each test re-creates object it seems so setting to class allows for it to get set only once
    dir = tempfile.gettempdir()
    FULL_PATH = os.sep.join((dir, tmp_file_name))
    if os.path.exists(FULL_PATH):
        fh = open(FULL_PATH, 'r')
        RAND = fh.read().strip()
        fh.close()
    else:
        RAND = str(int(random.random()*1000000))

    @classmethod
    def setUpClass(cls):
        cls._b = Beanstalk()
        cls.app = 'app-' + BasicSuite.RAND
        cls.app_ver = 'ver-' + BasicSuite.RAND
        cls.template = 'temp-' + BasicSuite.RAND
        cls.env = 'env-' + BasicSuite.RAND
    @classmethod
    def tearDownClass(cls): pass
    def setUp(self): pass
    def tearDown(self): pass

    @classmethod
    def _env_ready(cls, env_name):
        res = cls._b.describe_environments(application_name=cls.app, environment_names=env_name)
        status = res.environments[0].status
        if status != 'Ready':
            raise Exception('environment is not ready')

    @classmethod
    def _wait_for_env(cls, env_name):
        env_ok = False
        while not env_ok:
            try:
                cls._env_ready(env_name)
                env_ok = True
            except:
                time.sleep(15)

    @classmethod
    def _save_rand_file(cls):
        fh = open(BasicSuite.FULL_PATH, 'w')
        fh.write(BasicSuite.RAND)
        fh.close()

    @classmethod
    def _delete_rand_file(cls):
        if os.path.exists(BasicSuite.FULL_PATH):
            os.remove(BasicSuite.FULL_PATH)

class EnvNeeded(BasicSuite):
    @classmethod
    def setUpClass(cls):
        super(EnvNeeded, cls).setUpClass()
        cls._wait_for_env(cls.env)

class MiscSuite(BasicSuite):
    def test_01_check_dns_availability(self):
        res = self.__class__._b.check_dns_availability('amazon')
        self.assertIsInstance(res, response.CheckDNSAvailabilityResponse, 'correct response object returned')
        self.assertFalse(res.available, 'reasonable values in return object')
    '''
    def test_02_validate_configuration_settings(self):
        res = self.__class__._b.validate_configuration_settings('amazon')
        self.assertIsInstance(res, response.ValidateConfigurationSettingsResponse, 'correct response object returned')
    '''

class CreateSuite(BasicSuite):
    @classmethod
    def tearDownClass(cls):
        super(CreateSuite, cls).tearDownClass()
        cls._save_rand_file()

    def test_03_create_application(self):
        res = self.__class__._b.create_application(application_name=self.__class__.app)
        self.assertIsInstance(res, response.CreateApplicationResponse, 'correct response object returned')
    def test_04_create_application_version(self):
        res = self.__class__._b.create_application_version(application_name=self.__class__.app, version_label=self.__class__.app_ver)
        self.assertIsInstance(res, response.CreateApplicationVersionResponse, 'correct response object returned')
    def test_05_create_configuration_template(self):
        res = self.__class__._b.create_configuration_template(application_name=self.__class__.app, template_name=self.__class__.template)
        self.assertIsInstance(res, response.CreateConfigurationTemplateResponse, 'correct response object returned')
    def test_06_create_environment(self):
        res = self.__class__._b.create_environment(application_name=self.__class__.app, template_name=self.__class__.template, environment_name=self.__class__.env)
        self.assertIsInstance(res, response.CreateEnvironmentResponse, 'correct response object returned')
    def test_07_create_storage_location(self):
        res = self.__class__._b.create_storage_location()
        self.assertIsInstance(res, response.CreateStorageLocationResponse, 'correct response object returned')

class GetSuite(BasicSuite):
    def test_08_describe_applications(self):
        res = self.__class__._b.describe_applications()
        self.assertIsInstance(res, response.DescribeApplicationsResponse, 'correct response object returned')
    def test_09_describe_application_versions(self):
        res = self.__class__._b.describe_application_versions()
        self.assertIsInstance(res, response.DescribeApplicationVersionsResponse, 'correct response object returned')
    def test_10_describe_configuration_options(self):
        res = self.__class__._b.describe_configuration_options()
        self.assertIsInstance(res, response.DescribeConfigurationOptionsResponse, 'correct response object returned')
    def test_11_describe_configuration_settings(self):
        res = self.__class__._b.describe_configuration_settings(application_name=self.__class__.app, environment_name=self.__class__.env)
        self.assertIsInstance(res, response.DescribeConfigurationSettingsResponse, 'correct response object returned')
    def test_12_describe_environments(self):
        res = self.__class__._b.describe_environments()
        self.assertIsInstance(res, response.DescribeEnvironmentsResponse, 'correct response object returned')
    def test_13_describe_environment_resources(self):
        res = self.__class__._b.describe_environment_resources(environment_name=self.__class__.env)
        self.assertIsInstance(res, response.DescribeEnvironmentResourcesResponse, 'correct response object returned')
    def test_14_describe_events(self):
        res = self.__class__._b.describe_events()
        self.assertIsInstance(res, response.DescribeEventsResponse, 'correct response object returned')
    def test_15_list_available_solution_stacks(self):
        res = self.__class__._b.list_available_solution_stacks()
        self.assertIsInstance(res, response.ListAvailableSolutionStacksResponse, 'correct response object returned')

class ActionSuite(EnvNeeded):
    def test_16_request_environment_info(self):
        res = self.__class__._b.request_environment_info(environment_name=self.__class__.env, info_type='tail')
        self.assertIsInstance(res, response.RequestEnvironmentInfoResponse, 'correct response object returned')
    def test_17_retrieve_environment_info(self):
        res = self.__class__._b.retrieve_environment_info(environment_name=self.__class__.env, info_type='tail')
        self.assertIsInstance(res, response.RetrieveEnvironmentInfoResponse, 'correct response object returned')
    def test_18_rebuild_environment(self):
        res = self.__class__._b.rebuild_environment(environment_name=self.__class__.env)
        self.assertIsInstance(res, response.RebuildEnvironmentResponse, 'correct response object returned')
    def test_19_restart_app_server(self):
        self.__class__._wait_for_env(self.__class__.env)
        res = self.__class__._b.restart_app_server(environment_name=self.__class__.env)
        self.assertIsInstance(res, response.RestartAppServerResponse, 'correct response object returned')

class UpdateSuite(EnvNeeded):
    @classmethod
    def setUpClass(cls):
        super(UpdateSuite, cls).setUpClass()
        cls._b.create_environment(application_name=cls.app, template_name=cls.template, environment_name=cls.env+'X')

    @classmethod
    def tearDownClass(cls):
        super(UpdateSuite, cls).tearDownClass()
        cls._wait_for_env(cls.env)
        cls._wait_for_env(cls.env+'X')
        cls._b.swap_environment_cnames(source_environment_name=cls.env+'X', destination_environment_name=cls.env)
        cls._wait_for_env(cls.env+'X')
        cls._b.terminate_environment(environment_name=cls.env+'X')

    def test_20_update_application(self):
        res = self.__class__._b.update_application(application_name=self.__class__.app)
        self.assertIsInstance(res, response.UpdateApplicationResponse, 'correct response object returned')
    def test_21_update_application_version(self):
        res = self.__class__._b.update_application_version(application_name=self.__class__.app, version_label=self.__class__.app_ver)
        self.assertIsInstance(res, response.UpdateApplicationVersionResponse, 'correct response object returned')
    def test_22_update_configuration_template(self):
        res = self.__class__._b.update_configuration_template(application_name=self.__class__.app, template_name=self.__class__.template)
        self.assertIsInstance(res, response.UpdateConfigurationTemplateResponse, 'correct response object returned')
    def test_23_update_environment(self):
        res = self.__class__._b.update_environment(environment_name=self.__class__.env)
        self.assertIsInstance(res, response.UpdateEnvironmentResponse, 'correct response object returned')
    def test_24_swap_environment_cnames(self):
        self.__class__._wait_for_env(self.__class__.env+'X')
        res = self.__class__._b.swap_environment_cnames(source_environment_name=self.__class__.env, destination_environment_name=self.__class__.env+'X')
        self.assertIsInstance(res, response.SwapEnvironmentCNAMEsResponse, 'correct response object returned')

class DeleteSuite(EnvNeeded):
    @classmethod
    def tearDownClass(cls):
        super(DeleteSuite, cls).tearDownClass()
        cls._delete_rand_file()

    def test_25_delete_environment_configuration(self):
        res = self.__class__._b.delete_environment_configuration(application_name=self.__class__.app, environment_name=self.__class__.env)
        self.assertIsInstance(res, response.DeleteEnvironmentConfigurationResponse, 'correct response object returned')
    def test_26_terminate_environment(self):
        res = self.__class__._b.terminate_environment(environment_name=self.__class__.env)
        self.assertIsInstance(res, response.TerminateEnvironmentResponse, 'correct response object returned')
    def test_27_delete_configuration_template(self):
        res = self.__class__._b.delete_configuration_template(application_name=self.__class__.app, template_name=self.__class__.template)
        self.assertIsInstance(res, response.DeleteConfigurationTemplateResponse, 'correct response object returned')
    def test_28_delete_application_version(self):
        res = self.__class__._b.delete_application_version(application_name=self.__class__.app, version_label=self.__class__.app_ver)
        self.assertIsInstance(res, response.DeleteApplicationVersionResponse, 'correct response object returned')
    def test_29_delete_application(self):
        res = self.__class__._b.delete_application(application_name=self.__class__.app)
        self.assertIsInstance(res, response.DeleteApplicationResponse, 'correct response object returned')


if __name__ == '__main__':
    misc = unittest.TestLoader().loadTestsFromTestCase(MiscSuite)
    create = unittest.TestLoader().loadTestsFromTestCase(CreateSuite)
    get = unittest.TestLoader().loadTestsFromTestCase(GetSuite)
    action = unittest.TestLoader().loadTestsFromTestCase(ActionSuite)
    update = unittest.TestLoader().loadTestsFromTestCase(UpdateSuite)
    delete = unittest.TestLoader().loadTestsFromTestCase(DeleteSuite)
    suite = unittest.TestSuite([misc, create, get, action, update, delete])
    unittest.TextTestRunner().run(suite)
