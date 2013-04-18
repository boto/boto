# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

import json
import boto
from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo
from boto.exception import JSONResponseError
from boto.opsworks import exceptions


class OpsWorksConnection(AWSQueryConnection):
    """
    AWS OpsWorks
    """
    APIVersion = "2013-02-18"
    DefaultRegionName = "us-east-1"
    DefaultRegionEndpoint = "opsworks.us-east-1.amazonaws.com"
    ServiceName = "OpsWorks"
    TargetPrefix = "OpsWorks_20130218"
    ResponseError = JSONResponseError

    _faults = {
        "ResourceNotFoundException": exceptions.ResourceNotFoundException,
        "ValidationException": exceptions.ValidationException,
    }


    def __init__(self, **kwargs):
        region = kwargs.get('region')
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        kwargs['host'] = region.endpoint
        AWSQueryConnection.__init__(self, **kwargs)
        self.region = region

    def _required_auth_capability(self):
        return ['hmac-v4']

    def clone_stack(self, source_stack_id, service_role_arn, name=None,
                    region=None, attributes=None,
                    default_instance_profile_arn=None, default_os=None,
                    hostname_theme=None, default_availability_zone=None,
                    custom_json=None, use_custom_cookbooks=None,
                    custom_cookbooks_source=None, default_ssh_key_name=None,
                    clone_permissions=None, clone_app_ids=None):
        """
        Creates a clone of a specified stack.

        :type source_stack_id: string
        :param source_stack_id: The source stack ID.

        :type name: string
        :param name: The cloned stack name.

        :type region: string
        :param region: The cloned stack AWS region, such as "us-west-2". For
            more information about AWS regions, see `Regions and Endpoints`_

        :type attributes: map
        :param attributes: A list of stack attributes and values as key/value
            pairs to be added to the cloned stack.

        :type service_role_arn: string
        :param service_role_arn: The stack AWS Identity and Access Management
            (IAM) role, which allows OpsWorks to work with AWS resources on
            your behalf. You must set this parameter to the Amazon Resource
            Name (ARN) for an existing IAM role. If you create a stack by using
            the OpsWorks console, it creates the role for you. You can obtain
            an existing stack's IAM ARN programmatically by calling
            DescribePermissions. For more information about IAM ARNs, see
            `Using Identifiers`_.

        :type default_instance_profile_arn: string
        :param default_instance_profile_arn: The ARN of an IAM profile that is
            the default profile for all of the stack's EC2 instances. For more
            information about IAM ARNs, see `Using Identifiers`_.

        :type default_os: string
        :param default_os: The cloned stack default operating system, which
            must be either "Amazon Linux" or "Ubuntu 12.04 LTS".

        :type hostname_theme: string
        :param hostname_theme: The stack's host name theme, with spaces are
            replaced by underscores. The theme is used to generate hostnames
            for the stack's instances. By default, `HostnameTheme` is set to
            Layer_Dependent, which creates hostnames by appending integers to
            the layer's shortname. The other themes are:

        + Baked_Goods
        + Clouds
        + European_Cities
        + Fruits
        + Greek_Deities
        + Legendary_Creatures_from_Japan
        + Planets_and_Moons
        + Roman_Deities
        + Scottish_Islands
        + US_Cities
        + Wild_Cats


        To obtain a generated hostname, call `GetHostNameSuggestion`, which
            returns a hostname based on the current theme.

        :type default_availability_zone: string
        :param default_availability_zone: The cloned stack's Availability Zone.
            For more information, see `Regions and Endpoints`_.

        :type custom_json: string
        :param custom_json:
        A string that contains user-defined, custom JSON. It is used to
            override the corresponding default stack configuration JSON values.
            The string should be in the following format and must escape
            characters such as '"'.:
        `"{\"key1\": \"value1\", \"key2\": \"value2\",...}"`

        :type use_custom_cookbooks: boolean
        :param use_custom_cookbooks: Whether to use custom cookbooks.

        :type custom_cookbooks_source: dict
        :param custom_cookbooks_source:

        :type default_ssh_key_name: string
        :param default_ssh_key_name: A default SSH key for the stack instances.
            You can override this value when you create or update an instance.

        :type clone_permissions: boolean
        :param clone_permissions: Whether to clone the source stack's
            permissions.

        :type clone_app_ids: list
        :param clone_app_ids: A list of source stack app IDs to be included in
            the cloned stack.

        """
        params = {
            'SourceStackId': source_stack_id,
            'ServiceRoleArn': service_role_arn,
        }
        if name is not None:
            params['Name'] = name
        if region is not None:
            params['Region'] = region
        if attributes is not None:
            params['Attributes'] = attributes
        if default_instance_profile_arn is not None:
            params['DefaultInstanceProfileArn'] = default_instance_profile_arn
        if default_os is not None:
            params['DefaultOs'] = default_os
        if hostname_theme is not None:
            params['HostnameTheme'] = hostname_theme
        if default_availability_zone is not None:
            params['DefaultAvailabilityZone'] = default_availability_zone
        if custom_json is not None:
            params['CustomJson'] = custom_json
        if use_custom_cookbooks is not None:
            params['UseCustomCookbooks'] = use_custom_cookbooks
        if custom_cookbooks_source is not None:
            params['CustomCookbooksSource'] = custom_cookbooks_source
        if default_ssh_key_name is not None:
            params['DefaultSshKeyName'] = default_ssh_key_name
        if clone_permissions is not None:
            params['ClonePermissions'] = clone_permissions
        if clone_app_ids is not None:
            params['CloneAppIds'] = clone_app_ids
        return self.make_request(action='CloneStack',
                                 body=json.dumps(params))

    def create_app(self, stack_id, name, type, description=None,
                   app_source=None, domains=None, enable_ssl=None,
                   ssl_configuration=None, attributes=None):
        """
        Creates an app for a specified stack.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type name: string
        :param name: The app name.

        :type description: string
        :param description: A description of the app.

        :type type: string
        :param type: The app type. Each supported type is associated with a
            particular layer. For example, PHP applications are associated with
            a PHP layer. OpsWorks deploys an application to those instances
            that are members of the corresponding layer.

        :type app_source: dict
        :param app_source: A `Source` object that specifies the app repository.

        :type domains: list
        :param domains: The app virtual host settings, with multiple domains
            separated by commas. For example: `'www.mysite.com, mysite.com'`

        :type enable_ssl: boolean
        :param enable_ssl: Whether to enable SSL for the app.

        :type ssl_configuration: dict
        :param ssl_configuration: An `SslConfiguration` object with the SSL
            configuration.

        :type attributes: map
        :param attributes: One or more user-defined key/value pairs to be added
            to the stack attributes bag.

        """
        params = {'StackId': stack_id, 'Name': name, 'Type': type, }
        if description is not None:
            params['Description'] = description
        if app_source is not None:
            params['AppSource'] = app_source
        if domains is not None:
            params['Domains'] = domains
        if enable_ssl is not None:
            params['EnableSsl'] = enable_ssl
        if ssl_configuration is not None:
            params['SslConfiguration'] = ssl_configuration
        if attributes is not None:
            params['Attributes'] = attributes
        return self.make_request(action='CreateApp',
                                 body=json.dumps(params))

    def create_deployment(self, stack_id, command, app_id=None,
                          instance_ids=None, comment=None, custom_json=None):
        """
        Deploys a stack or app.


        + App deployment generates a `deploy` event, which runs the
          associated recipes and passes them a JSON stack configuration
          object that includes information about the app.
        + Stack deployment runs the `deploy` recipes but does not
          raise an event.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type app_id: string
        :param app_id: The app ID, for app deployments.

        :type instance_ids: list
        :param instance_ids: The instance IDs for the deployment targets.

        :type command: dict
        :param command: A `DeploymentCommand` object that describes details of
            the operation.

        :type comment: string
        :param comment: A user-defined comment.

        :type custom_json: string
        :param custom_json:
        A string that contains user-defined, custom JSON. It is used to
            override the corresponding default stack configuration JSON values.
            The string should be in the following format and must escape
            characters such as '"'.:
        `"{\"key1\": \"value1\", \"key2\": \"value2\",...}"`

        """
        params = {'StackId': stack_id, 'Command': command, }
        if app_id is not None:
            params['AppId'] = app_id
        if instance_ids is not None:
            params['InstanceIds'] = instance_ids
        if comment is not None:
            params['Comment'] = comment
        if custom_json is not None:
            params['CustomJson'] = custom_json
        return self.make_request(action='CreateDeployment',
                                 body=json.dumps(params))

    def create_instance(self, stack_id, layer_ids, instance_type,
                        auto_scaling_type=None, hostname=None, os=None,
                        ssh_key_name=None, availability_zone=None):
        """
        Creates an instance in a specified stack.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type layer_ids: list
        :param layer_ids: An array that contains the instance layer IDs.

        :type instance_type: string
        :param instance_type:
        The instance type, which can be one of the following:


        + m1.small
        + m1.medium
        + m1.large
        + m1.xlarge
        + c1.medium
        + c1.xlarge
        + m2.xlarge
        + m2.2xlarge
        + m2.4xlarge

        :type auto_scaling_type: string
        :param auto_scaling_type:
        The instance auto scaling type, which has three possible values:


        + **AlwaysRunning**: A 24x7 instance, which is not affected by auto
              scaling.
        + **TimeBasedAutoScaling**: A time-based auto scaling instance, which
              is started and stopped based on a specified schedule. To specify
              the schedule, call SetTimeBasedAutoScaling.
        + **LoadBasedAutoScaling**: A load-based auto scaling instance, which
              is started and stopped based on load metrics. To use load-based
              auto scaling, you must enable it for the instance layer and
              configure the thresholds by calling SetLoadBasedAutoScaling.

        :type hostname: string
        :param hostname: The instance host name.

        :type os: string
        :param os: The instance operating system.

        :type ssh_key_name: string
        :param ssh_key_name: The instance SSH key name.

        :type availability_zone: string
        :param availability_zone: The instance Availability Zone. For more
            information, see `Regions and Endpoints`_.

        """
        params = {
            'StackId': stack_id,
            'LayerIds': layer_ids,
            'InstanceType': instance_type,
        }
        if auto_scaling_type is not None:
            params['AutoScalingType'] = auto_scaling_type
        if hostname is not None:
            params['Hostname'] = hostname
        if os is not None:
            params['Os'] = os
        if ssh_key_name is not None:
            params['SshKeyName'] = ssh_key_name
        if availability_zone is not None:
            params['AvailabilityZone'] = availability_zone
        return self.make_request(action='CreateInstance',
                                 body=json.dumps(params))

    def create_layer(self, stack_id, type, name, shortname, attributes=None,
                     custom_instance_profile_arn=None,
                     custom_security_group_ids=None, packages=None,
                     volume_configurations=None, enable_auto_healing=None,
                     auto_assign_elastic_ips=None, custom_recipes=None):
        """
        Creates a layer.

        :type stack_id: string
        :param stack_id: The layer stack ID.

        :type type: string
        :param type: The layer type. A stack cannot have more than one layer of
            the same type.

        :type name: string
        :param name: The layer name, which is used by the console.

        :type shortname: string
        :param shortname: The layer short name, which is used internally by
            OpsWorks and by Chef recipes. The shortname is also used as the
            name for the directory where your app files are installed. It can
            have a maximum of 200 characters, which are limited to the
            alphanumeric characters, '-', '_', and '.'.

        :type attributes: map
        :param attributes: One or more user-defined key/value pairs to be added
            to the stack attributes bag.

        :type custom_instance_profile_arn: string
        :param custom_instance_profile_arn: The ARN of an IAM profile that to
            be used for the layer's EC2 instances. For more information about
            IAM ARNs, see `Using Identifiers`_.

        :type custom_security_group_ids: list
        :param custom_security_group_ids: An array containing the layer custom
            security group IDs.

        :type packages: list
        :param packages: An array of `Package` objects that describe the layer
            packages.

        :type volume_configurations: list
        :param volume_configurations: A `VolumeConfigurations` object that
            describes the layer Amazon EBS volumes.

        :type enable_auto_healing: boolean
        :param enable_auto_healing: Whether to disable auto healing for the
            layer.

        :type auto_assign_elastic_ips: boolean
        :param auto_assign_elastic_ips: Whether to automatically assign an
            `Elastic IP address`_ to the layer.

        :type custom_recipes: dict
        :param custom_recipes: A `LayerCustomRecipes` object that specifies the
            layer custom recipes.

        """
        params = {
            'StackId': stack_id,
            'Type': type,
            'Name': name,
            'Shortname': shortname,
        }
        if attributes is not None:
            params['Attributes'] = attributes
        if custom_instance_profile_arn is not None:
            params['CustomInstanceProfileArn'] = custom_instance_profile_arn
        if custom_security_group_ids is not None:
            params['CustomSecurityGroupIds'] = custom_security_group_ids
        if packages is not None:
            params['Packages'] = packages
        if volume_configurations is not None:
            params['VolumeConfigurations'] = volume_configurations
        if enable_auto_healing is not None:
            params['EnableAutoHealing'] = enable_auto_healing
        if auto_assign_elastic_ips is not None:
            params['AutoAssignElasticIps'] = auto_assign_elastic_ips
        if custom_recipes is not None:
            params['CustomRecipes'] = custom_recipes
        return self.make_request(action='CreateLayer',
                                 body=json.dumps(params))

    def create_stack(self, name, region, service_role_arn,
                     default_instance_profile_arn, attributes=None,
                     default_os=None, hostname_theme=None,
                     default_availability_zone=None, custom_json=None,
                     use_custom_cookbooks=None, custom_cookbooks_source=None,
                     default_ssh_key_name=None):
        """
        Creates a new stack.

        :type name: string
        :param name: The stack name.

        :type region: string
        :param region: The stack AWS region, such as "us-west-2". For more
            information about Amazon regions, see `Regions and Endpoints`_.

        :type attributes: map
        :param attributes: One or more user-defined key/value pairs to be added
            to the stack attributes bag.

        :type service_role_arn: string
        :param service_role_arn: The stack AWS Identity and Access Management
            (IAM) role, which allows OpsWorks to work with AWS resources on
            your behalf. You must set this parameter to the Amazon Resource
            Name (ARN) for an existing IAM role. For more information about IAM
            ARNs, see `Using Identifiers`_.

        :type default_instance_profile_arn: string
        :param default_instance_profile_arn: The ARN of an IAM profile that is
            the default profile for all of the stack's EC2 instances. For more
            information about IAM ARNs, see `Using Identifiers`_.

        :type default_os: string
        :param default_os: The cloned stack default operating system, which
            must be either "Amazon Linux" or "Ubuntu 12.04 LTS".

        :type hostname_theme: string
        :param hostname_theme: The stack's host name theme, with spaces are
            replaced by underscores. The theme is used to generate hostnames
            for the stack's instances. By default, `HostnameTheme` is set to
            Layer_Dependent, which creates hostnames by appending integers to
            the layer's shortname. The other themes are:

        + Baked_Goods
        + Clouds
        + European_Cities
        + Fruits
        + Greek_Deities
        + Legendary_Creatures_from_Japan
        + Planets_and_Moons
        + Roman_Deities
        + Scottish_Islands
        + US_Cities
        + Wild_Cats


        To obtain a generated hostname, call `GetHostNameSuggestion`, which
            returns a hostname based on the current theme.

        :type default_availability_zone: string
        :param default_availability_zone: The stack default Availability Zone.
            For more information, see `Regions and Endpoints`_.

        :type custom_json: string
        :param custom_json:
        A string that contains user-defined, custom JSON. It is used to
            override the corresponding default stack configuration JSON values.
            The string should be in the following format and must escape
            characters such as '"'.:
        `"{\"key1\": \"value1\", \"key2\": \"value2\",...}"`

        :type use_custom_cookbooks: boolean
        :param use_custom_cookbooks: Whether the stack uses custom cookbooks.

        :type custom_cookbooks_source: dict
        :param custom_cookbooks_source:

        :type default_ssh_key_name: string
        :param default_ssh_key_name: A default SSH key for the stack instances.
            You can override this value when you create or update an instance.

        """
        params = {
            'Name': name,
            'Region': region,
            'ServiceRoleArn': service_role_arn,
            'DefaultInstanceProfileArn': default_instance_profile_arn,
        }
        if attributes is not None:
            params['Attributes'] = attributes
        if default_os is not None:
            params['DefaultOs'] = default_os
        if hostname_theme is not None:
            params['HostnameTheme'] = hostname_theme
        if default_availability_zone is not None:
            params['DefaultAvailabilityZone'] = default_availability_zone
        if custom_json is not None:
            params['CustomJson'] = custom_json
        if use_custom_cookbooks is not None:
            params['UseCustomCookbooks'] = use_custom_cookbooks
        if custom_cookbooks_source is not None:
            params['CustomCookbooksSource'] = custom_cookbooks_source
        if default_ssh_key_name is not None:
            params['DefaultSshKeyName'] = default_ssh_key_name
        return self.make_request(action='CreateStack',
                                 body=json.dumps(params))

    def create_user_profile(self, iam_user_arn, ssh_username=None,
                            ssh_public_key=None):
        """
        Creates a new user.

        :type iam_user_arn: string
        :param iam_user_arn: The user's IAM ARN.

        :type ssh_username: string
        :param ssh_username: The user's SSH user name.

        :type ssh_public_key: string
        :param ssh_public_key: The user's public SSH key.

        """
        params = {'IamUserArn': iam_user_arn, }
        if ssh_username is not None:
            params['SshUsername'] = ssh_username
        if ssh_public_key is not None:
            params['SshPublicKey'] = ssh_public_key
        return self.make_request(action='CreateUserProfile',
                                 body=json.dumps(params))

    def delete_app(self, app_id):
        """
        Deletes a specified app.

        :type app_id: string
        :param app_id: The app ID.

        """
        params = {'AppId': app_id, }
        return self.make_request(action='DeleteApp',
                                 body=json.dumps(params))

    def delete_instance(self, instance_id, delete_elastic_ip=None,
                        delete_volumes=None):
        """
        Deletes a specified instance.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type delete_elastic_ip: boolean
        :param delete_elastic_ip: Whether to delete the instance Elastic IP
            address.

        :type delete_volumes: boolean
        :param delete_volumes: Whether to delete the instance Amazon EBS
            volumes.

        """
        params = {'InstanceId': instance_id, }
        if delete_elastic_ip is not None:
            params['DeleteElasticIp'] = delete_elastic_ip
        if delete_volumes is not None:
            params['DeleteVolumes'] = delete_volumes
        return self.make_request(action='DeleteInstance',
                                 body=json.dumps(params))

    def delete_layer(self, layer_id):
        """
        Deletes a specified layer. You must first remove all
        associated instances.

        :type layer_id: string
        :param layer_id: The layer ID.

        """
        params = {'LayerId': layer_id, }
        return self.make_request(action='DeleteLayer',
                                 body=json.dumps(params))

    def delete_stack(self, stack_id):
        """
        Deletes a specified stack. You must first delete all instances
        and layers.

        :type stack_id: string
        :param stack_id: The stack ID.

        """
        params = {'StackId': stack_id, }
        return self.make_request(action='DeleteStack',
                                 body=json.dumps(params))

    def delete_user_profile(self, iam_user_arn):
        """
        Deletes a user.

        :type iam_user_arn: string
        :param iam_user_arn: The user's IAM ARN.

        """
        params = {'IamUserArn': iam_user_arn, }
        return self.make_request(action='DeleteUserProfile',
                                 body=json.dumps(params))

    def describe_apps(self, stack_id=None, app_ids=None):
        """
        Requests a description of a specified set of apps.

        :type stack_id: string
        :param stack_id:
        The app stack ID.

        :type app_ids: list
        :param app_ids: An array of app IDs for the apps to be described.

        """
        params = {}
        if stack_id is not None:
            params['StackId'] = stack_id
        if app_ids is not None:
            params['AppIds'] = app_ids
        return self.make_request(action='DescribeApps',
                                 body=json.dumps(params))

    def describe_commands(self, deployment_id=None, instance_id=None,
                          command_ids=None):
        """
        Describes the results of specified commands.

        :type deployment_id: string
        :param deployment_id: The deployment ID.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type command_ids: list
        :param command_ids: An array of IDs for the commands to be described.

        """
        params = {}
        if deployment_id is not None:
            params['DeploymentId'] = deployment_id
        if instance_id is not None:
            params['InstanceId'] = instance_id
        if command_ids is not None:
            params['CommandIds'] = command_ids
        return self.make_request(action='DescribeCommands',
                                 body=json.dumps(params))

    def describe_deployments(self, stack_id=None, app_id=None,
                             deployment_ids=None):
        """
        Requests a description of a specified set of deployments.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type app_id: string
        :param app_id: The app ID.

        :type deployment_ids: list
        :param deployment_ids: An array of deployment IDs to be described.

        """
        params = {}
        if stack_id is not None:
            params['StackId'] = stack_id
        if app_id is not None:
            params['AppId'] = app_id
        if deployment_ids is not None:
            params['DeploymentIds'] = deployment_ids
        return self.make_request(action='DescribeDeployments',
                                 body=json.dumps(params))

    def describe_elastic_ips(self, instance_id=None, ips=None):
        """
        Describes an instance's `Elastic IP addresses`_.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type ips: list
        :param ips: An array of Elastic IP addresses to be described.

        """
        params = {}
        if instance_id is not None:
            params['InstanceId'] = instance_id
        if ips is not None:
            params['Ips'] = ips
        return self.make_request(action='DescribeElasticIps',
                                 body=json.dumps(params))

    def describe_instances(self, stack_id=None, layer_id=None, app_id=None,
                           instance_ids=None):
        """
        Requests a description of a set of instances associated with a
        specified ID or IDs.

        :type stack_id: string
        :param stack_id: A stack ID.

        :type layer_id: string
        :param layer_id: A layer ID.

        :type app_id: string
        :param app_id: An app ID.

        :type instance_ids: list
        :param instance_ids: An array of instance IDs to be described.

        """
        params = {}
        if stack_id is not None:
            params['StackId'] = stack_id
        if layer_id is not None:
            params['LayerId'] = layer_id
        if app_id is not None:
            params['AppId'] = app_id
        if instance_ids is not None:
            params['InstanceIds'] = instance_ids
        return self.make_request(action='DescribeInstances',
                                 body=json.dumps(params))

    def describe_layers(self, stack_id, layer_ids=None):
        """
        Requests a description of one or more layers in a specified
        stack.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type layer_ids: list
        :param layer_ids: An array of layer IDs that specify the layers to be
            described.

        """
        params = {'StackId': stack_id, }
        if layer_ids is not None:
            params['LayerIds'] = layer_ids
        return self.make_request(action='DescribeLayers',
                                 body=json.dumps(params))

    def describe_load_based_auto_scaling(self, layer_ids):
        """
        Describes load-based auto scaling configurations for specified
        layers.

        :type layer_ids: list
        :param layer_ids: An array of layer IDs.

        """
        params = {'LayerIds': layer_ids, }
        return self.make_request(action='DescribeLoadBasedAutoScaling',
                                 body=json.dumps(params))

    def describe_permissions(self, iam_user_arn, stack_id):
        """
        Describes the permissions for a specified stack. You must
        specify at least one of the two request values.

        :type iam_user_arn: string
        :param iam_user_arn: The user's IAM ARN. For more information about IAM
            ARNs, see `Using Identifiers`_.

        :type stack_id: string
        :param stack_id: The stack ID.

        """
        params = {'IamUserArn': iam_user_arn, 'StackId': stack_id, }
        return self.make_request(action='DescribePermissions',
                                 body=json.dumps(params))

    def describe_raid_arrays(self, instance_id=None, raid_array_ids=None):
        """
        Describe an instance's RAID arrays.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type raid_array_ids: list
        :param raid_array_ids: An array of RAID array IDs to be described.

        """
        params = {}
        if instance_id is not None:
            params['InstanceId'] = instance_id
        if raid_array_ids is not None:
            params['RaidArrayIds'] = raid_array_ids
        return self.make_request(action='DescribeRaidArrays',
                                 body=json.dumps(params))

    def describe_service_errors(self, stack_id=None, instance_id=None,
                                service_error_ids=None):
        """
        Describes OpsWorks service errors.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type service_error_ids: list
        :param service_error_ids: An array of service error IDs to be
            described.

        """
        params = {}
        if stack_id is not None:
            params['StackId'] = stack_id
        if instance_id is not None:
            params['InstanceId'] = instance_id
        if service_error_ids is not None:
            params['ServiceErrorIds'] = service_error_ids
        return self.make_request(action='DescribeServiceErrors',
                                 body=json.dumps(params))

    def describe_stacks(self, stack_ids=None):
        """
        Requests a description of one or more stacks.

        :type stack_ids: list
        :param stack_ids: An array of stack IDs that specify the stacks to be
            described.

        """
        params = {}
        if stack_ids is not None:
            params['StackIds'] = stack_ids
        return self.make_request(action='DescribeStacks',
                                 body=json.dumps(params))

    def describe_time_based_auto_scaling(self, instance_ids):
        """
        Describes time-based auto scaling configurations for specified
        instances.

        :type instance_ids: list
        :param instance_ids: An array of instance IDs.

        """
        params = {'InstanceIds': instance_ids, }
        return self.make_request(action='DescribeTimeBasedAutoScaling',
                                 body=json.dumps(params))

    def describe_user_profiles(self, iam_user_arns):
        """
        Describe specified users.

        :type iam_user_arns: list
        :param iam_user_arns: An array of IAM user ARNs that identify the users
            to be described.

        """
        params = {'IamUserArns': iam_user_arns, }
        return self.make_request(action='DescribeUserProfiles',
                                 body=json.dumps(params))

    def describe_volumes(self, instance_id=None, raid_array_id=None,
                         volume_ids=None):
        """
        Describes an instance's Amazon EBS volumes.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type raid_array_id: string
        :param raid_array_id: The RAID array ID.

        :type volume_ids: list
        :param volume_ids: Am array of volume IDs to be described.

        """
        params = {}
        if instance_id is not None:
            params['InstanceId'] = instance_id
        if raid_array_id is not None:
            params['RaidArrayId'] = raid_array_id
        if volume_ids is not None:
            params['VolumeIds'] = volume_ids
        return self.make_request(action='DescribeVolumes',
                                 body=json.dumps(params))

    def get_hostname_suggestion(self, layer_id):
        """
        Gets a generated hostname for the specified layer, based on
        the current hostname theme.

        :type layer_id: string
        :param layer_id: The layer ID.

        """
        params = {'LayerId': layer_id, }
        return self.make_request(action='GetHostnameSuggestion',
                                 body=json.dumps(params))

    def reboot_instance(self, instance_id):
        """
        Reboots a specified instance.

        :type instance_id: string
        :param instance_id: The instance ID.

        """
        params = {'InstanceId': instance_id, }
        return self.make_request(action='RebootInstance',
                                 body=json.dumps(params))

    def set_load_based_auto_scaling(self, layer_id, enable=None,
                                    up_scaling=None, down_scaling=None):
        """
        Specify the load-based auto scaling configuration for a
        specified layer.

        To use load-based auto scaling, you must create a set of load-
        based auto scaling instances. Load-based auto scaling operates
        only on the instances from that set, so you must ensure that
        you have created enough instances to handle the maximum
        anticipated load.

        :type layer_id: string
        :param layer_id: The layer ID.

        :type enable: boolean
        :param enable: Enables load-based auto scaling for the layer.

        :type up_scaling: dict
        :param up_scaling: An `AutoScalingThresholds` object with the upscaling
            threshold configuration. If the load exceeds these thresholds for a
            specified amount of time, OpsWorks starts a specified number of
            instances.

        :type down_scaling: dict
        :param down_scaling: An `AutoScalingThresholds` object with the
            downscaling threshold configuration. If the load falls below these
            thresholds for a specified amount of time, OpsWorks stops a
            specified number of instances.

        """
        params = {'LayerId': layer_id, }
        if enable is not None:
            params['Enable'] = enable
        if up_scaling is not None:
            params['UpScaling'] = up_scaling
        if down_scaling is not None:
            params['DownScaling'] = down_scaling
        return self.make_request(action='SetLoadBasedAutoScaling',
                                 body=json.dumps(params))

    def set_permission(self, stack_id, iam_user_arn, allow_ssh=None,
                       allow_sudo=None):
        """
        Specifies a stack's permissions.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type iam_user_arn: string
        :param iam_user_arn: The user's IAM ARN.

        :type allow_ssh: boolean
        :param allow_ssh: The user is allowed to use SSH to communicate with
            the instance.

        :type allow_sudo: boolean
        :param allow_sudo: The user is allowed to use **sudo** to elevate
            privileges.

        """
        params = {'StackId': stack_id, 'IamUserArn': iam_user_arn, }
        if allow_ssh is not None:
            params['AllowSsh'] = allow_ssh
        if allow_sudo is not None:
            params['AllowSudo'] = allow_sudo
        return self.make_request(action='SetPermission',
                                 body=json.dumps(params))

    def set_time_based_auto_scaling(self, instance_id,
                                    auto_scaling_schedule=None):
        """
        Specify the time-based auto scaling configuration for a
        specified instance.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type auto_scaling_schedule: dict
        :param auto_scaling_schedule: An `AutoScalingSchedule` with the
            instance schedule.

        """
        params = {'InstanceId': instance_id, }
        if auto_scaling_schedule is not None:
            params['AutoScalingSchedule'] = auto_scaling_schedule
        return self.make_request(action='SetTimeBasedAutoScaling',
                                 body=json.dumps(params))

    def start_instance(self, instance_id):
        """
        Starts a specified instance.

        :type instance_id: string
        :param instance_id: The instance ID.

        """
        params = {'InstanceId': instance_id, }
        return self.make_request(action='StartInstance',
                                 body=json.dumps(params))

    def start_stack(self, stack_id):
        """
        Starts stack's instances.

        :type stack_id: string
        :param stack_id: The stack ID.

        """
        params = {'StackId': stack_id, }
        return self.make_request(action='StartStack',
                                 body=json.dumps(params))

    def stop_instance(self, instance_id):
        """
        Stops a specified instance. When you stop a standard instance,
        the data disappears and must be reinstalled when you restart
        the instance. You can stop an Amazon EBS-backed instance
        without losing data.

        :type instance_id: string
        :param instance_id: The instance ID.

        """
        params = {'InstanceId': instance_id, }
        return self.make_request(action='StopInstance',
                                 body=json.dumps(params))

    def stop_stack(self, stack_id):
        """
        Stops a specified stack.

        :type stack_id: string
        :param stack_id: The stack ID.

        """
        params = {'StackId': stack_id, }
        return self.make_request(action='StopStack',
                                 body=json.dumps(params))

    def update_app(self, app_id, name=None, description=None, type=None,
                   app_source=None, domains=None, enable_ssl=None,
                   ssl_configuration=None, attributes=None):
        """
        Updates a specified app.

        :type app_id: string
        :param app_id: The app ID.

        :type name: string
        :param name: The app name.

        :type description: string
        :param description: A description of the app.

        :type type: string
        :param type: The app type.

        :type app_source: dict
        :param app_source: A `Source` object that specifies the app repository.

        :type domains: list
        :param domains: The app's virtual host settings, with multiple domains
            separated by commas. For example: `'www.mysite.com, mysite.com'`

        :type enable_ssl: boolean
        :param enable_ssl: Whether SSL is enabled for the app.

        :type ssl_configuration: dict
        :param ssl_configuration: An `SslConfiguration` object with the SSL
            configuration.

        :type attributes: map
        :param attributes: One or more user-defined key/value pairs to be added
            to the stack attributes bag.

        """
        params = {'AppId': app_id, }
        if name is not None:
            params['Name'] = name
        if description is not None:
            params['Description'] = description
        if type is not None:
            params['Type'] = type
        if app_source is not None:
            params['AppSource'] = app_source
        if domains is not None:
            params['Domains'] = domains
        if enable_ssl is not None:
            params['EnableSsl'] = enable_ssl
        if ssl_configuration is not None:
            params['SslConfiguration'] = ssl_configuration
        if attributes is not None:
            params['Attributes'] = attributes
        return self.make_request(action='UpdateApp',
                                 body=json.dumps(params))

    def update_instance(self, instance_id, layer_ids=None,
                        instance_type=None, auto_scaling_type=None,
                        hostname=None, os=None, ssh_key_name=None):
        """
        Updates a specified instance.

        :type instance_id: string
        :param instance_id: The instance ID.

        :type layer_ids: list
        :param layer_ids: The instance's layer IDs.

        :type instance_type: string
        :param instance_type:
        The instance type, which can be one of the following:


        + m1.small
        + m1.medium
        + m1.large
        + m1.xlarge
        + c1.medium
        + c1.xlarge
        + m2.xlarge
        + m2.2xlarge
        + m2.4xlarge

        :type auto_scaling_type: string
        :param auto_scaling_type:
        The instance's auto scaling type, which has three possible values:


        + **AlwaysRunning**: A 24x7 instance, which is not affected by auto
              scaling.
        + **TimeBasedAutoScaling**: A time-based auto scaling instance, which
              is started and stopped based on a specified schedule.
        + **LoadBasedAutoScaling**: A load-based auto scaling instance, which
              is started and stopped based on load metrics.

        :type hostname: string
        :param hostname: The instance host name.

        :type os: string
        :param os: The instance operating system.

        :type ssh_key_name: string
        :param ssh_key_name: The instance SSH key name.

        """
        params = {'InstanceId': instance_id, }
        if layer_ids is not None:
            params['LayerIds'] = layer_ids
        if instance_type is not None:
            params['InstanceType'] = instance_type
        if auto_scaling_type is not None:
            params['AutoScalingType'] = auto_scaling_type
        if hostname is not None:
            params['Hostname'] = hostname
        if os is not None:
            params['Os'] = os
        if ssh_key_name is not None:
            params['SshKeyName'] = ssh_key_name
        return self.make_request(action='UpdateInstance',
                                 body=json.dumps(params))

    def update_layer(self, layer_id, name=None, shortname=None,
                     attributes=None, custom_instance_profile_arn=None,
                     custom_security_group_ids=None, packages=None,
                     volume_configurations=None, enable_auto_healing=None,
                     auto_assign_elastic_ips=None, custom_recipes=None):
        """
        Updates a specified layer.

        :type layer_id: string
        :param layer_id: The layer ID.

        :type name: string
        :param name: The layer name, which is used by the console.

        :type shortname: string
        :param shortname: The layer short name, which is used internally by
            OpsWorks, by Chef. The shortname is also used as the name for the
            directory where your app files are installed. It can have a maximum
            of 200 characters and must be in the following format:
            /\A[a-z0-9\-\_\.]+\Z/.

        :type attributes: map
        :param attributes: One or more user-defined key/value pairs to be added
            to the stack attributes bag.

        :type custom_instance_profile_arn: string
        :param custom_instance_profile_arn: The ARN of an IAM profile to be
            used for all of the layer's EC2 instances. For more information
            about IAM ARNs, see `Using Identifiers`_.

        :type custom_security_group_ids: list
        :param custom_security_group_ids: An array containing the layer's
            custom security group IDs.

        :type packages: list
        :param packages: An array of `Package` objects that describe the
            layer's packages.

        :type volume_configurations: list
        :param volume_configurations: A `VolumeConfigurations` object that
            describes the layer's Amazon EBS volumes.

        :type enable_auto_healing: boolean
        :param enable_auto_healing: Whether to disable auto healing for the
            layer.

        :type auto_assign_elastic_ips: boolean
        :param auto_assign_elastic_ips: Whether to automatically assign an
            `Elastic IP address`_ to the layer.

        :type custom_recipes: dict
        :param custom_recipes: A `LayerCustomRecipes` object that specifies the
            layer's custom recipes.

        """
        params = {'LayerId': layer_id, }
        if name is not None:
            params['Name'] = name
        if shortname is not None:
            params['Shortname'] = shortname
        if attributes is not None:
            params['Attributes'] = attributes
        if custom_instance_profile_arn is not None:
            params['CustomInstanceProfileArn'] = custom_instance_profile_arn
        if custom_security_group_ids is not None:
            params['CustomSecurityGroupIds'] = custom_security_group_ids
        if packages is not None:
            params['Packages'] = packages
        if volume_configurations is not None:
            params['VolumeConfigurations'] = volume_configurations
        if enable_auto_healing is not None:
            params['EnableAutoHealing'] = enable_auto_healing
        if auto_assign_elastic_ips is not None:
            params['AutoAssignElasticIps'] = auto_assign_elastic_ips
        if custom_recipes is not None:
            params['CustomRecipes'] = custom_recipes
        return self.make_request(action='UpdateLayer',
                                 body=json.dumps(params))

    def update_stack(self, stack_id, name=None, attributes=None,
                     service_role_arn=None,
                     default_instance_profile_arn=None, default_os=None,
                     hostname_theme=None, default_availability_zone=None,
                     custom_json=None, use_custom_cookbooks=None,
                     custom_cookbooks_source=None, default_ssh_key_name=None):
        """
        Updates a specified stack.

        :type stack_id: string
        :param stack_id: The stack ID.

        :type name: string
        :param name: The stack's new name.

        :type attributes: map
        :param attributes: One or more user-defined key/value pairs to be added
            to the stack attributes bag.

        :type service_role_arn: string
        :param service_role_arn: The stack AWS Identity and Access Management
            (IAM) role, which allows OpsWorks to work with AWS resources on
            your behalf. You must set this parameter to the Amazon Resource
            Name (ARN) for an existing IAM role. For more information about IAM
            ARNs, see `Using Identifiers`_.

        :type default_instance_profile_arn: string
        :param default_instance_profile_arn: The ARN of an IAM profile that is
            the default profile for all of the stack's EC2 instances. For more
            information about IAM ARNs, see `Using Identifiers`_.

        :type default_os: string
        :param default_os: The cloned stack default operating system, which
            must be either "Amazon Linux" or "Ubuntu 12.04 LTS".

        :type hostname_theme: string
        :param hostname_theme: The stack's new host name theme, with spaces are
            replaced by underscores. The theme is used to generate hostnames
            for the stack's instances. By default, `HostnameTheme` is set to
            Layer_Dependent, which creates hostnames by appending integers to
            the layer's shortname. The other themes are:

        + Baked_Goods
        + Clouds
        + European_Cities
        + Fruits
        + Greek_Deities
        + Legendary_Creatures_from_Japan
        + Planets_and_Moons
        + Roman_Deities
        + Scottish_Islands
        + US_Cities
        + Wild_Cats


        To obtain a generated hostname, call `GetHostNameSuggestion`, which
            returns a hostname based on the current theme.

        :type default_availability_zone: string
        :param default_availability_zone: The stack new default Availability
            Zone. For more information, see `Regions and Endpoints`_.

        :type custom_json: string
        :param custom_json:
        A string that contains user-defined, custom JSON. It is used to
            override the corresponding default stack configuration JSON values.
            The string should be in the following format and must escape
            characters such as '"'.:
        `"{\"key1\": \"value1\", \"key2\": \"value2\",...}"`

        :type use_custom_cookbooks: boolean
        :param use_custom_cookbooks: Whether the stack uses custom cookbooks.

        :type custom_cookbooks_source: dict
        :param custom_cookbooks_source:

        :type default_ssh_key_name: string
        :param default_ssh_key_name: A default SSH key for the stack instances.
            You can override this value when you create or update an instance.

        """
        params = {'StackId': stack_id, }
        if name is not None:
            params['Name'] = name
        if attributes is not None:
            params['Attributes'] = attributes
        if service_role_arn is not None:
            params['ServiceRoleArn'] = service_role_arn
        if default_instance_profile_arn is not None:
            params['DefaultInstanceProfileArn'] = default_instance_profile_arn
        if default_os is not None:
            params['DefaultOs'] = default_os
        if hostname_theme is not None:
            params['HostnameTheme'] = hostname_theme
        if default_availability_zone is not None:
            params['DefaultAvailabilityZone'] = default_availability_zone
        if custom_json is not None:
            params['CustomJson'] = custom_json
        if use_custom_cookbooks is not None:
            params['UseCustomCookbooks'] = use_custom_cookbooks
        if custom_cookbooks_source is not None:
            params['CustomCookbooksSource'] = custom_cookbooks_source
        if default_ssh_key_name is not None:
            params['DefaultSshKeyName'] = default_ssh_key_name
        return self.make_request(action='UpdateStack',
                                 body=json.dumps(params))

    def update_user_profile(self, iam_user_arn, ssh_username=None,
                            ssh_public_key=None):
        """
        Updates a specified user's SSH name and public key.

        :type iam_user_arn: string
        :param iam_user_arn: The user IAM ARN.

        :type ssh_username: string
        :param ssh_username: The user's new SSH user name.

        :type ssh_public_key: string
        :param ssh_public_key: The user's new SSH public key.

        """
        params = {'IamUserArn': iam_user_arn, }
        if ssh_username is not None:
            params['SshUsername'] = ssh_username
        if ssh_public_key is not None:
            params['SshPublicKey'] = ssh_public_key
        return self.make_request(action='UpdateUserProfile',
                                 body=json.dumps(params))

    def make_request(self, action, body):
        headers = {
            'X-Amz-Target': '%s.%s' % (self.TargetPrefix, action),
            'Host': self.region.endpoint,
            'Content-Type': 'application/x-amz-json-1.1',
            'Content-Length': str(len(body)),
        }
        http_request = self.build_base_http_request(
            method='POST', path='/', auth_path='/', params={},
            headers=headers, data=body)
        response = self._mexe(http_request, sender=None,
                              override_num_retries=10)
        response_body = response.read()
        boto.log.debug(response_body)
        if response.status == 200:
            if response_body:
                return json.loads(response_body)
        else:
            json_body = json.loads(response_body)
            fault_name = json_body.get('__type', None)
            exception_class = self._faults.get(fault_name, self.ResponseError)
            raise exception_class(response.status, response.reason,
                                  body=json_body)

