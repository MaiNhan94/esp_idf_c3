# Copyright 2015-2017 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" IDF Test Applications """
import hashlib
import json
import os
import re
import subprocess
import sys
from abc import abstractmethod

from tiny_test_fw import App
from .IDFAssignTest import ExampleGroup, TestAppsGroup, UnitTestGroup, IDFCaseGroup, ComponentUTGroup

try:
    import gitlab_api
except ImportError:
    gitlab_api = None


def parse_flash_settings(path):
    file_name = os.path.basename(path)
    if file_name == "flasher_args.json":
        # CMake version using build metadata file
        with open(path, "r") as f:
            args = json.load(f)
        flash_files = [(offs, binary) for (offs, binary) in args["flash_files"].items() if offs != ""]
        flash_settings = args["flash_settings"]
        app_name = os.path.splitext(args["app"]["file"])[0]
    else:
        # GNU Make version uses download.config arguments file
        with open(path, "r") as f:
            args = f.readlines()[-1].split(" ")
            flash_files = []
            flash_settings = {}
            for idx in range(0, len(args), 2):  # process arguments in pairs
                if args[idx].startswith("--"):
                    # strip the -- from the command line argument
                    flash_settings[args[idx][2:]] = args[idx + 1]
                else:
                    # offs, filename
                    flash_files.append((args[idx], args[idx + 1]))
            # we can only guess app name in download.config.
            for p in flash_files:
                if not os.path.dirname(p[1]) and "partition" not in p[1]:
                    # app bin usually in the same dir with download.config and it's not partition table
                    app_name = os.path.splitext(p[1])[0]
                    break
            else:
                app_name = None
    return flash_files, flash_settings, app_name


class Artifacts(object):
    def __init__(self, dest_root_path, artifact_index_file, app_path, config_name, target):
        assert gitlab_api
        # at least one of app_path or config_name is not None. otherwise we can't match artifact
        assert app_path or config_name
        assert os.path.exists(artifact_index_file)
        self.gitlab_inst = gitlab_api.Gitlab(os.getenv("CI_PROJECT_ID"))
        self.dest_root_path = dest_root_path
        with open(artifact_index_file, "r") as f:
            artifact_index = json.load(f)
        self.artifact_info = self._find_artifact(artifact_index, app_path, config_name, target)

    @staticmethod
    def _find_artifact(artifact_index, app_path, config_name, target):
        for artifact_info in artifact_index:
            match_result = True
            if app_path:
                # We use endswith here to avoid issue like:
                # examples_protocols_mqtt_ws but return a examples_protocols_mqtt_wss failure
                match_result = artifact_info["app_dir"].endswith(app_path)
            if config_name:
                match_result = match_result and config_name == artifact_info["config"]
            if target:
                match_result = match_result and target == artifact_info["target"]
            if match_result:
                ret = artifact_info
                break
        else:
            ret = None
        return ret

    def _get_app_base_path(self):
        if self.artifact_info:
            return os.path.join(self.artifact_info["work_dir"], self.artifact_info["build_dir"])
        else:
            return None

    def _get_flash_arg_file(self, base_path, job_id):
        if self.artifact_info["build_system"] == "cmake":
            flash_arg_file = os.path.join(base_path, "flasher_args.json")
        else:
            flash_arg_file = os.path.join(base_path, "download.config")

        self.gitlab_inst.download_artifact(job_id, [flash_arg_file], self.dest_root_path)
        return flash_arg_file

    def _download_binary_files(self, base_path, job_id, flash_arg_file):
        flash_files, flash_settings, app_name = parse_flash_settings(os.path.join(self.dest_root_path,
                                                                                  flash_arg_file))
        artifact_files = [os.path.join(base_path, p[1]) for p in flash_files]
        artifact_files.append(os.path.join(base_path, app_name + ".elf"))

        self.gitlab_inst.download_artifact(job_id, artifact_files, self.dest_root_path)

    def _download_sdkconfig_file(self, base_path, job_id):
        self.gitlab_inst.download_artifact(job_id, [os.path.join(os.path.dirname(base_path), "sdkconfig")],
                                           self.dest_root_path)

    def download_artifacts(self):
        if not self.artifact_info:
            return None
        base_path = self._get_app_base_path()
        job_id = self.artifact_info["ci_job_id"]
        # 1. download flash args file
        flash_arg_file = self._get_flash_arg_file(base_path, job_id)

        # 2. download all binary files
        self._download_binary_files(base_path, job_id, flash_arg_file)

        # 3. download sdkconfig file
        self._download_sdkconfig_file(base_path, job_id)
        return base_path

    def download_artifact_files(self, file_names):
        if self.artifact_info:
            base_path = os.path.join(self.artifact_info["work_dir"], self.artifact_info["build_dir"])
            job_id = self.artifact_info["ci_job_id"]

            # download all binary files
            artifact_files = [os.path.join(base_path, fn) for fn in file_names]
            self.gitlab_inst.download_artifact(job_id, artifact_files, self.dest_root_path)

            # download sdkconfig file
            self.gitlab_inst.download_artifact(job_id, [os.path.join(os.path.dirname(base_path), "sdkconfig")],
                                               self.dest_root_path)
        else:
            base_path = None
        return base_path


class UnitTestArtifacts(Artifacts):
    BUILDS_DIR_RE = re.compile(r'^builds/')

    def _get_app_base_path(self):
        if self.artifact_info:
            output_dir = self.BUILDS_DIR_RE.sub('output/', self.artifact_info["build_dir"])
            return os.path.join(self.artifact_info["app_dir"], output_dir)
        else:
            return None

    def _download_sdkconfig_file(self, base_path, job_id):
        self.gitlab_inst.download_artifact(job_id, [os.path.join(base_path, "sdkconfig")], self.dest_root_path)


class IDFApp(App.BaseApp):
    """
    Implements common esp-idf application behavior.
    idf applications should inherent from this class and overwrite method get_binary_path.
    """

    IDF_DOWNLOAD_CONFIG_FILE = "download.config"
    IDF_FLASH_ARGS_FILE = "flasher_args.json"

    def __init__(self, app_path, config_name=None, target=None, case_group=IDFCaseGroup, artifact_cls=Artifacts):
        super(IDFApp, self).__init__(app_path)
        self.app_path = app_path
        self.config_name = config_name
        self.target = target
        self.idf_path = self.get_sdk_path()
        self.case_group = case_group
        self.artifact_cls = artifact_cls
        self.binary_path = self.get_binary_path()
        self.elf_file = self._get_elf_file_path()
        self._elf_file_sha256 = None
        assert os.path.exists(self.binary_path)
        if self.IDF_DOWNLOAD_CONFIG_FILE not in os.listdir(self.binary_path):
            if self.IDF_FLASH_ARGS_FILE not in os.listdir(self.binary_path):
                msg = ("Neither {} nor {} exists. "
                       "Try to run 'make print_flash_cmd | tail -n 1 > {}/{}' "
                       "or 'idf.py build' "
                       "for resolving the issue."
                       "").format(self.IDF_DOWNLOAD_CONFIG_FILE, self.IDF_FLASH_ARGS_FILE,
                                  self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)
                raise AssertionError(msg)

        self.flash_files, self.flash_settings = self._parse_flash_download_config()
        self.partition_table = self._parse_partition_table()

    def __str__(self):
        parts = ['app<{}>'.format(self.app_path)]
        if self.config_name:
            parts.append('config<{}>'.format(self.config_name))
        if self.target:
            parts.append('target<{}>'.format(self.target))
        return ' '.join(parts)

    @classmethod
    def get_sdk_path(cls):  # type: () -> str
        idf_path = os.getenv("IDF_PATH")
        assert idf_path
        assert os.path.exists(idf_path)
        return idf_path

    def _get_sdkconfig_paths(self):
        """
        returns list of possible paths where sdkconfig could be found

        Note: could be overwritten by a derived class to provide other locations or order
        """
        return [os.path.join(self.binary_path, "sdkconfig"), os.path.join(self.binary_path, "..", "sdkconfig")]

    def get_sdkconfig(self):
        """
        reads sdkconfig and returns a dictionary with all configured variables

        :raise: AssertionError: if sdkconfig file does not exist in defined paths
        """
        d = {}
        sdkconfig_file = None
        for i in self._get_sdkconfig_paths():
            if os.path.exists(i):
                sdkconfig_file = i
                break
        assert sdkconfig_file is not None
        with open(sdkconfig_file) as f:
            for line in f:
                configs = line.split('=')
                if len(configs) == 2:
                    d[configs[0]] = configs[1].rstrip()
        return d

    @abstractmethod
    def _try_get_binary_from_local_fs(self):
        pass

    def get_binary_path(self):
        path = self._try_get_binary_from_local_fs()
        if path:
            return path

        artifacts = self.artifact_cls(self.idf_path,
                                      self.case_group.get_artifact_index_file(),
                                      self.app_path, self.config_name, self.target)
        if isinstance(self, LoadableElfTestApp):
            assert self.app_files
            path = artifacts.download_artifact_files(self.app_files)
        else:
            path = artifacts.download_artifacts()

        if path:
            return os.path.join(self.idf_path, path)
        else:
            raise OSError("Failed to get binary for {}".format(self))

    def _get_elf_file_path(self):
        ret = ""
        file_names = os.listdir(self.binary_path)
        for fn in file_names:
            if os.path.splitext(fn)[1] == ".elf":
                ret = os.path.join(self.binary_path, fn)
        return ret

    def _parse_flash_download_config(self):
        """
        Parse flash download config from build metadata files

        Sets self.flash_files, self.flash_settings

        (Called from constructor)

        Returns (flash_files, flash_settings)
        """

        if self.IDF_FLASH_ARGS_FILE in os.listdir(self.binary_path):
            # CMake version using build metadata file
            path = os.path.join(self.binary_path, self.IDF_FLASH_ARGS_FILE)
        else:
            # GNU Make version uses download.config arguments file
            path = os.path.join(self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)

        flash_files, flash_settings, app_name = parse_flash_settings(path)
        # The build metadata file does not currently have details, which files should be encrypted and which not.
        # Assume that all files should be encrypted if flash encryption is enabled in development mode.
        sdkconfig_dict = self.get_sdkconfig()
        flash_settings["encrypt"] = "CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT" in sdkconfig_dict

        # make file offsets into integers, make paths absolute
        flash_files = [(int(offs, 0), os.path.join(self.binary_path, file_path.strip())) for (offs, file_path) in flash_files]

        return flash_files, flash_settings

    def _parse_partition_table(self):
        """
        Parse partition table contents based on app binaries

        Returns partition_table data

        (Called from constructor)
        """
        partition_tool = os.path.join(self.idf_path,
                                      "components",
                                      "partition_table",
                                      "gen_esp32part.py")
        assert os.path.exists(partition_tool)

        errors = []
        # self.flash_files is sorted based on offset in order to have a consistent result with different versions of
        # Python
        for (_, path) in sorted(self.flash_files, key=lambda elem: elem[0]):
            if 'partition' in os.path.split(path)[1]:
                partition_file = os.path.join(self.binary_path, path)

                process = subprocess.Popen([sys.executable, partition_tool, partition_file],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (raw_data, raw_error) = process.communicate()
                if isinstance(raw_error, bytes):
                    raw_error = raw_error.decode()
                if 'Traceback' in raw_error:
                    # Some exception occurred. It is possible that we've tried the wrong binary file.
                    errors.append((path, raw_error))
                    continue

                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode()
                break
        else:
            traceback_msg = os.linesep.join(['{} {}:{}{}'.format(partition_tool,
                                                                 p,
                                                                 os.linesep,
                                                                 msg) for p, msg in errors])
            raise ValueError("No partition table found for IDF binary path: {}{}{}".format(self.binary_path,
                                                                                           os.linesep,
                                                                                           traceback_msg))

        partition_table = dict()
        for line in raw_data.splitlines():
            if line[0] != "#":
                try:
                    _name, _type, _subtype, _offset, _size, _flags = line.split(",")
                    if _size[-1] == "K":
                        _size = int(_size[:-1]) * 1024
                    elif _size[-1] == "M":
                        _size = int(_size[:-1]) * 1024 * 1024
                    else:
                        _size = int(_size)
                    _offset = int(_offset, 0)
                except ValueError:
                    continue
                partition_table[_name] = {
                    "type": _type,
                    "subtype": _subtype,
                    "offset": _offset,
                    "size": _size,
                    "flags": _flags
                }

        return partition_table

    def get_elf_sha256(self):
        if self._elf_file_sha256:
            return self._elf_file_sha256

        sha256 = hashlib.sha256()
        with open(self.elf_file, 'rb') as f:
            sha256.update(f.read())
        self._elf_file_sha256 = sha256.hexdigest()
        return self._elf_file_sha256


class Example(IDFApp):
    def __init__(self, app_path, config_name='default', target='esp32', case_group=ExampleGroup, artifacts_cls=Artifacts):
        if not config_name:
            config_name = 'default'
        if not target:
            target = 'esp32'
        super(Example, self).__init__(app_path, config_name, target, case_group, artifacts_cls)

    def _get_sdkconfig_paths(self):
        """
        overrides the parent method to provide exact path of sdkconfig for example tests
        """
        return [os.path.join(self.binary_path, "..", "sdkconfig")]

    def _try_get_binary_from_local_fs(self):
        # build folder of example path
        path = os.path.join(self.idf_path, self.app_path, "build")
        if os.path.exists(path):
            return path

        # Search for CI build folders.
        # Path format: $IDF_PATH/build_examples/app_path_with_underscores/config/target
        # (see tools/ci/build_examples.sh)
        # For example: $IDF_PATH/build_examples/examples_get-started_blink/default/esp32
        app_path_underscored = self.app_path.replace(os.path.sep, "_")
        example_path = os.path.join(self.idf_path, self.case_group.LOCAL_BUILD_DIR)
        for dirpath in os.listdir(example_path):
            if os.path.basename(dirpath) == app_path_underscored:
                path = os.path.join(example_path, dirpath, self.config_name, self.target, "build")
                if os.path.exists(path):
                    return path
                else:
                    return None


class UT(IDFApp):
    def __init__(self, app_path, config_name='default', target='esp32', case_group=UnitTestGroup, artifacts_cls=UnitTestArtifacts):
        if not config_name:
            config_name = 'default'
        if not target:
            target = 'esp32'
        super(UT, self).__init__(app_path, config_name, target, case_group, artifacts_cls)

    def _try_get_binary_from_local_fs(self):
        path = os.path.join(self.idf_path, self.app_path, "build")
        if os.path.exists(path):
            return path

        # first try to get from build folder of unit-test-app
        path = os.path.join(self.idf_path, "tools", "unit-test-app", "build")
        if os.path.exists(path):
            # found, use bin in build path
            return path

        # ``build_unit_test.sh`` will copy binary to output folder
        path = os.path.join(self.idf_path, "tools", "unit-test-app", "output", self.target, self.config_name)
        if os.path.exists(path):
            return path

        return None


class TestApp(Example):
    def __init__(self, app_path, config_name='default', target='esp32', case_group=TestAppsGroup, artifacts_cls=Artifacts):
        super(TestApp, self).__init__(app_path, config_name, target, case_group, artifacts_cls)


class ComponentUTApp(TestApp):
    def __init__(self, app_path, config_name='default', target='esp32', case_group=ComponentUTGroup, artifacts_cls=Artifacts):
        super(ComponentUTApp, self).__init__(app_path, config_name, target, case_group, artifacts_cls)


class LoadableElfTestApp(TestApp):
    def __init__(self, app_path, app_files, config_name='default', target='esp32', case_group=TestAppsGroup, artifacts_cls=Artifacts):
        # add arg `app_files` for loadable elf test_app.
        # Such examples only build elf files, so it doesn't generate flasher_args.json.
        # So we can't get app files from config file. Test case should pass it to application.
        super(IDFApp, self).__init__(app_path)
        self.app_path = app_path
        self.app_files = app_files
        self.config_name = config_name or 'default'
        self.target = target or 'esp32'
        self.idf_path = self.get_sdk_path()
        self.case_group = case_group
        self.artifact_cls = artifacts_cls
        self.binary_path = self.get_binary_path()
        self.elf_file = self._get_elf_file_path()
        assert os.path.exists(self.binary_path)


class SSC(IDFApp):
    def get_binary_path(self):
        # TODO: to implement SSC get binary path
        return self.app_path


class AT(IDFApp):
    def get_binary_path(self):
        # TODO: to implement AT get binary path
        return self.app_path
