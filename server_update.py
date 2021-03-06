import tempfile
import urllib.request
from urllib.error import URLError
import os
import shutil
import json
import sys
from math import ceil
import traceback
import argparse

"""
A Set of tools to automate the server update process.
Error philosophy:
 > As long as it is LOGGED or DISPLAYED somewhere for the user to see, it has been handled.
 """


def output(text):

    """
    Outputs text to the terminal via print,
    will not print content if we are in quiet mode.
    """

    if not args.quiet:

        # We are not quieted, print the content

        print(text)


def error_report(exc, net=False):

    """
    Function for displaying error information to the terminal
    :param exc: Exception object
    :param net: Whether to include network information
    :return:
    """

    print("+==================================================+")
    print("  [ --== The Following Error Has Occurred: ==-- ]")
    print("+==================================================+")

    # Print error name

    print("Error Name: {}".format(exc))
    print("+==================================================+")

    # Print full traceback:

    print("Full Traceback:")
    traceback.print_exc()

    if net:

        # Include extra network information

        print("+==================================================+")
        print("Extra Network Information:")

        if hasattr(exc, 'reason'):

            print("We failed to reach the server.")
            print("Reason: {}".format(exc.reason))

        if hasattr(exc, 'code'):

            print("The server could not fulfill the request.")
            print("Error code: {}".format(exc.code))

    print("+==================================================+")
    print("(Can you make anything of this?)")
    print("Please check the github page for more info: https://github.com/Owen-Cochell/PaperMC-Update.")

    return


class Update:

    """
    Server updater, handles checking, downloading, and installing.
    """

    def __init__(self, ver):

        self.ver = ver  # Version of the minecraft server we are currently using.
        self._base = 'https://papermc.io/api/v1/paper'  # Base URL to build of off
        self._headers = {
             'Content-Type': 'application/json;charset=UTF-8',
             'Accept': 'application/json, text/plain, */*',
             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:43.0) Gecko/20100101 Firefox/43.0',
             'Accept-Language': 'en-US,en;q=0.5',
             'DNT': '1',
         }  # Request headers for contacting Paper Download API, emulating a Google client

    def _progress_bar(self, total, step, end, prefix="", size=60, prog_char="#", empty_char="."):

        """
        Outputs a simple progress bar to stdout
        :param total: Total amount of computations
        :param step: Amount to increase the counter by
        :param end:  Number to end on
        :param prefix: What to show before the progress bar
        :param size: Size of the progress bar
        :return:
        """

        # Iterating over the total number of iterations:

        for i in range(total):

            # Yield i

            yield i

            # Calculate number of '#' to render:

            x = int(size*(i+1)/total)

            # Rendering progress bar:

            if not args.quiet:

                sys.stdout.write("{}[{}{}] {}/{}\r".format(prefix, prog_char*x, empty_char*(size-x),
                                                           (i*step if i < total - 1 else end), end))
                sys.stdout.flush()

        # Writing newline, to continue execution

        if not args.quiet:

            sys.stdout.write("\n")
            sys.stdout.flush()

    def _url_report(self, point):

        """
        Reports an error during a request operation
        :param point: Point of failure
        :return:
        """

        print("\n+==================================================+")
        print("> !ATTENTION! >")
        print("An error occurred during a request operation.")
        print("Fail Point: {}".format(point))
        print("Your check/update operation will be canceled.")
        print("Detailed error info below:")

    def download(self, path, version, build_num='latest'):

        """
        Gets file from Paper API, and displays a progress bar
        Write to the file specified in chunks, as to not fill up the memory
        :param version: Version to download
        :param build_num: Build to download
        :param path: Path to file to write to
        :return: True on success, False on Failure
        """

        output("\n[ --== Starting Download: ==-- ]")

        # Building URL here:

        url = self._base + '/' + str(version) + '/' + str(build_num) + '/download'

        output("URL: {}".format(url))

        # Creating request here:

        req = urllib.request.Request(url, headers=self._headers)

        # Sending request to Paper API

        try:

            data = urllib.request.urlopen(req)

        except URLError as e:

            self._url_report("File Download")

            # Network error occurred

            error_report(e, net=True)

            return False

        # Getting content length of download:

        length = int(data.getheader('content-length'))
        blocksize = 4608

        output("Download Size: {}".format(length))

        file = open(path, mode='ba')

        # Using progress bar to visualise download:

        try:

            for i in self._progress_bar(ceil(length/blocksize) + 1, blocksize, length, prefix='Downloading:'):

                # Getting blocksize data:

                byts = data.read(blocksize)

                # Writing data to file:

                file.write(byts)

        except URLError as e:

            self._url_report("File Download")

            # Report the error

            error_report(e, net=True)

            file.close()

            return False

        except Exception as e:

            self._url_report("File Download")

            # Report the error

            error_report(e)

            file.close()

            return False

        # Closing file:

        file.close()

        # Done downloading

        output("[ --== Download Complete! ==-- ]")

        return True

    def _get(self, version=None, build_num=None):

        """
        Gets RAW data from the Paper API, version info only
        :param version: Version to include in the URL
        :param build_num: Build number to include in the URL
        :return: urllib Request object
        """

        # Building url:

        final = self._base

        if version is not None:

            # Specific version requested:

            final = final + '/' + str(version)

            if build_num is not None:

                # Specific build num requested:

                final = final + '/' + str(build_num)

        # Creating request here:

        req = urllib.request.Request(final, headers=self._headers)

        # Getting data:

        try:

            data = urllib.request.urlopen(req)

        except Exception as e:

            self._url_report("API Fetch Operation")

            # Exception occurred, handel it

            error_report(e, net=True)

            return None

        return data

    def get_versions(self):

        """
        Gets available versions of the server
        :return: List of available versions
        """

        # Getting raw data and converting it to JSON format

        output("  > Fetching and decoding version info...")

        data = self._get()

        if data is None:

            # Error occurred

            return None

        data = json.loads(data.read())

        # Returning version info

        output("  > Done fetching version information!")

        return data['versions']

    def get_buildnums(self, version):

        """
        Gets available build for a particular version
        :param version: Version to get builds for
        :return: List of builds
        """

        # Getting raw data and converting it to JSON format

        output("  > Fetching and decoding build info...")

        data = self._get(version=version)

        if data is None:

            # Error occurred

            return None

        data = json.loads(data.read())

        output("  > Done fetching build info!")

        return data['builds']['all']


class FileUtil:

    """
    Class for managing the creating/deleting/moving of server files
    """

    def __init__(self, path, config=None):

        self.path = path  # Path to file being updated
        self.temp = None  # Tempdir instance
        self.config_default = 'version_history.json'  # Default name of paper versioning file

    def create_temp_dir(self):

        """
        Creates a temporary directory
        :return: Temp file instance
        """

        self.temp = tempfile.TemporaryDirectory()

        return self.temp

    def close_temp_dir(self):

        """
        Closes created temporary directory
        :return:
        """

        self.temp.close()

    def load_config(self, config):

        """
        Loads configuration info from 'version.json' in the server directory
        We only load version info if it's in the official format!
        """

        config = (config if config is not None else os.path.join(os.path.dirname(self.path), self.config_default))

        output("# Checking configuration file at [{}] ...".format(config))

        if os.path.isfile(config):

            # Exists and is file, read it

            output("# Loading configuration data ...")

            try:

                file = open(config, 'r')

                data = json.load(file)

            except Exception as e:

                # Failed to load config data - not in JSON format

                print("# Failed to load config data - Not in JSON format!")

                return '0', 0

            # Read the data, and attempt to pull some info out of it

            current = data['currentVersion']

            if type(current) != str:

                # We only accept strings:

                print("# Failed to load config data - We want strings, not {}!".format(type(current)))

                return '0', 0

            # Catch any exceptions due to weird format conventions:

            try:

                # Splitting the data in two so we can pull some content out:

                build, version = current.split(" ", 1)

                # Getting build information:

                build = int(build.split("-")[-1])

                # Getting version information:

                version = version[5:-1]

            except Exception as e:

                # Weird file content. Unable to get info.

                print("# Unable to load config data - Invalid Format, we support official builds only!")

                return '0', 0

            # Returning version information:

            output("# Done loading configuration data! ")

            return version, build

        else:

            print("# Unable to load config data from file at [{}] - Not found/Not a file!".format(config))

            return '0', 0

    def _fail_install(self, point):

        """
        Shows where the error occurred during the installation
        :param point: Point of failure
        :return:
        """

        print("\n+==================================================+")
        print("> !ATTENTION! <")
        print("An error occurred during the installation, and we can not continue.")
        print("We will attempt to recover your previous installation(If applicable)")
        print("Fail point: {}".format(point))
        print("Detailed error info below:")

        return

    def install(self):

        """
        "Installs" the contents of the temporary file into the target in the root server directory.
        :return:
        """

        output("\n[ --== installation: ==-- ]")

        # Creating backup of old file:

        output("# Creating backup of previous installation...")

        try:

            shutil.copyfile(self.path, os.path.join(self.temp.name, 'backup'))

        except Exception as e:

            # Show install error

            self._fail_install("File Backup")

            # Show error info

            error_report(e)

            return False

        output("# Backup created at: {}".format(os.path.join(self.temp.name, 'backup')))

        # Removing current file:

        output("# Deleting current file at {}...".format(self.path))

        try:

            os.remove(self.path)

        except Exception as e:

            self._fail_install("Old File Deletion")

            # Showing error

            error_report(e)

            # Recovering backup

            self._recover_backup()

            return False

        output("# Removed original file!")

        # Copying downloaded file to root:

        try:

            output("# Copying download data to root directory...")
            output("# ({} > {})".format(os.path.join(self.temp.name, 'download_data'),
                                        self.path))

            shutil.copyfile(os.path.join(self.temp.name, 'download_data'), self.path)

        except Exception as e:

            # Install error

            self._fail_install("File Copy")

            # Show error

            error_report(e)

            # Recover backup

            self._recover_backup()

            return False

        output("# Done copying download data to root directory!")

        # Cleaning up temporary directory:

        output("# Cleaning up temporary directory...")

        self.temp.cleanup()

        output("# Done cleaning temporary directory!")

        output("[ --== installation complete! ==-- ]")

        return True

    def _recover_backup(self):

        """
        Recovers the backup of the old server jar file
        :return:
        """

        print("+==================================================+")
        print("\n> !ATTENTION! <")
        print("A failure has occurred during the installation process.")
        print("I'm sure you can see the error information above.")
        print("This script will attempt to recover your old installation.")
        print("If this operation fails, check the github page for more info: "
              "https://github.com/Owen-Cochell/PaperMC-Update")

        # Deleting file in root directory:

        print("# Deleting Corrupted temporary File...")

        try:

            os.remove(self.path)

        except FileNotFoundError:

            # File was not found. Continuing...

            print("# File not found. Continuing operation...")

        except Exception as e:

            print("# Critical error during recovery process!")
            print("# Displaying error information:")

            error_report(e)

            print("Your previous installation could not be recovered.")

            return False

        # Copying file to root directory:

        print("# Copying backup file[{}] to server root directory[{}]...".format(os.path.join(self.temp.name, 'backup'),
                                                                                 self.path))

        try:

            shutil.copyfile(os.path.join(self.temp.name, 'backup'), self.path)

        except Exception as e:

            print("# Critical error during recovery process!")
            print("# Displaying error information:")

            error_report(e)

            print("Your previous installation could not be recovered.")

            return False

        print("\nRecovery process complete!")
        print("Your file has been successfully recovered.")
        print("Please debug the situation, and figure out why the problem occurred,")
        print("Before re-trying the update process.")

        return True


class ServerUpdater:

    """
    Class that binds all server updater classes together
    """

    def __init__(self, path, config_file=None, version=None, build=None, config=True, prompt=True):

        self.version = version  # Version of minecraft server we are running
        self.fileutil = FileUtil(path)  # Fileutility instance
        self.buildnum = build  # Buildnum of the current server
        self._available_versions = []  # List of available versions
        self.prompt = prompt  # Whether to prompt the user for version selection
        self.config_file = config_file  # Name of the config file we pull version info from

        # Starting object

        self._start(config)

        self.update = Update(self.version)  # Updater Instance

    def _start(self, config):

        """
        Starts the object, loads configuration
        :return:
        """

        temp_version = '0'
        temp_build = 0

        if config:

            # Allowed to use configuration file

            temp_version, temp_build = self.fileutil.load_config(self.config_file)

        else:

            # Skipping config file

            output("# Skipping configuration file!")

        self.version = (self.version if self.version != '0' else temp_version)
        self.buildnum = (self.buildnum if self.buildnum != 0 else temp_build)

        output("\nServer Version Information:")
        output("  > Version: [{}]".format(self.version))
        output("  > Build: [{}]".format(self.buildnum))

        return

    def check(self):

        """
        Checks if a new version is available
        :return: True is new version, False if not/error
        """

        output("\n[ --== Checking For New Version: ==-- ]")

        # Checking for new server version

        output("# Comparing local <> remote server versions...")

        ver = self.update.get_versions()

        if ver is None:

            # Error occurred

            return False

        if ver[0] != self.version:

            # New version available!

            output("# New Version available! - [Version: {}]".format(ver[0]))
            output("[ --== Version check complete! ==-- ]\n")

            return True

        output("# No new version available.")

        # Checking builds

        output("# Comparing local <> remote builds...")

        build = self.update.get_buildnums(self.version)

        if build is None:

            # Error occurred

            return False

        if build[0] != str(self.buildnum):

            # New build available!

            output("# New build available! - [Build: {}]".format(build[0]))
            output("[ --== Version check complete! ==-- ]\n")

            return True

        output("# No new builds found.")
        output("[ --== Version check complete! ==-- ]\n")

        return False

    def _select(self, val, choice, default, name):

        """
        Selects a value from the choices.
        Support updater keywords
        :param val: Value entered
        :param choice: Choices to choose from
        :param default: Default value
        :param name: Name of value we are choosing
        :return: True if valid, false if invalid
        """

        if val == '':

            # User wants default value:

            val = default

        if val == 'latest':

            # User wants latest

            output("# Selecting latest {} - [{}]...".format(name, self._available_versions[0]))

            val = choice[0]

            return True, val

        if val not in choice:

            # User selected invalid option

            output("\n# Error: Invalid {} selected!".format(name))

            return False, ''

        # Option selected is valid. Continue

        output("# Selecting {}: [{}]...".format(name, val))

        return True, val

    def version_select(self, default_version='latest', default_build='latest'):

        """
        Prompts the user to select a version to download
        Checks input against values from Paper API
        Default value is recommended values
        :param default_build: Default build number
        :param default_version: Default version
        :return: (version, build)
        """

        # Checking if we have version information:

        output("# Checking version information...")

        if not self._available_versions:

            # Version information is empty, reloading

            output("# Loading version information...")

            data = self.update.get_versions()

            if data is None:

                # Error occurred

                return None, None

            self._available_versions = data

        if self.prompt:

            print("\n[ --== Version Select: ==-- ] ")

            print("\nPlease enter the version you would like to download:")
            print("Example: 14.4.4")
            print("(Tip: The value enclosed in brackets is the default option. Leave the prompt blank to accept it.)")
            print("(Tip: Enter 'latest' to select the latest version.)")

            print("\nAvailable versions:")

            # Displaying available versions

            for i in self._available_versions:

                print("  > Version: [{}]".format(i))

            while True:

                ver = input("\nEnter Version[{}]: ".format(default_version))

                stat, ver = self._select(ver, self._available_versions, default_version, "version")

                if stat:

                    # User selected okay value

                    break

        else:

            # Just select default version

            stat, ver = self._select('', self._available_versions, default_version, "version")

            if not stat:

                # Invalid version selected

                print("# Aborting installation!")

                return None, None

        # Getting build info

        output("# Loading build information...")

        nums = self.update.get_buildnums(ver)

        if nums is None:

            # Error occurred:

            return None, None

        if self.prompt:

            print("\nPlease enter the build you would like to download:")
            print("Example: 205")
            print("(Tip: The value enclosed in brackets is the default option. Leave the prompt blank to accept it.)")
            print("(Tip: Enter 'latest' to select the latest build.)")

            print("\nAvailable Builds:")

            # Displaying available builds

            for i in nums:

                print("  > Build Num: [{}]".format(i))

            while True:

                # Prompting user for build info

                build = input("\nEnter Build[{}]: ".format(default_build))

                stat, build = self._select(build, nums, default_build, "build")

                if stat:

                    # User selected okay value

                    break

        else:

            # Select default build

            stat, build = self._select('', nums, default_build, "build")

            if not stat:

                # Invalid build selected!

                output("# Aborting installation!")

                return None, None

        output("\nYou have selected:")
        output("   > Version: [{}]".format(ver))
        output("   > Build: [{}]".format(build))

        output("\n[ --== Version Selection Complete! ==-- ]")

        return ver, build

    def get_new(self, default_version='latest', default_build='latest'):

        """
        Downloads and installs the new version
        Prompts the user to select a specific version
        :return:
        """

        # Prompting user for version info:

        ver, build = self.version_select(default_version=default_version, default_build=default_build)

        if ver is None or build is None:

            # Error occurred, cancel installation

            return

        # Checking if user wants to continue with installation

        if self.prompt:

            print("\nDo you want to continue with the installation?")

            inp = input("(Y/N):").lower()

            if inp in ['n', 'no']:
                # User does not want to continue, exit

                output("Canceling installation...")

                return

        # Creating temporary directory to store assets:

        output("# Creating temporary directory...")

        self.fileutil.create_temp_dir()

        output("# Temporary directory created at: {}".format(self.fileutil.temp.name))

        # Starting download process:

        val = self.update.download(os.path.join(self.fileutil.temp.name, 'download_data'), ver, build_num=build)

        if not val:

            # Download process failed

            return

        # Download process complete!

        # Installing downloaded data:

        val = self.fileutil.install()

        if not val:

            # Install process failed

            return

        output("\nUpdate complete!")

        # Updating values

        self.version = ver
        self.buildnum = build

        return


if __name__ == '__main__':

    # Ran as script

    parser = argparse.ArgumentParser(description='PaperMC Server Updater.',
                                     epilog="Please check the github page for more info: "
                                            "https://github.com/Owen-Cochell/PaperMC-Update.")

    parser.add_argument('path', help='Path to file to be updated')
    parser.add_argument('-v', '--version', help='Server version to install(Sets default value)', default='latest')
    parser.add_argument('-b', '--build', help='Server build to install(Sets default value)', default='latest')
    parser.add_argument('-iv', help='Sets the currently installed server version, ignores config', default='0')
    parser.add_argument('-ib', help='Sets the currently installed server build, ignores config', default=0)
    parser.add_argument('-c', '--check-only', help='Checks for an update, does not install', action='store_true')
    parser.add_argument('-nc', '--no-check', help='Does not check for an update, skips to install', action='store_true')
    parser.add_argument('-i', '--interactive', help='Prompts the user for the version they would like to install',
                        action='store_true')
    parser.add_argument('-nlc', '--no-load-config', help='Will not load Paper version config.', action='store_false')
    parser.add_argument('-cf', '--config-file', help='Path to Paper configuration file to read from'
                                                     '(Defaults to [SERVER_JAR_DIR]/version_history.json)')
    parser.add_argument('-q', '--quiet', help="Will only output errors and interactive questions to the terminal",
                        action='store_true')

    # Deprecated arguments - Included for compatibility, but do nothing

    parser.add_argument('-ndc', '--no-dump-config', help=argparse.SUPPRESS, action='store_false')
    parser.add_argument('--config', help=argparse.SUPPRESS, default='NONE')
    parser.add_argument('-C', '--cleanup', help=argparse.SUPPRESS, action='store_true')

    args = parser.parse_args()

    output("+==========================================================================+")
    output(r'''|     _____                              __  __          __      __        |
|    / ___/___  ______   _____  _____   / / / /___  ____/ /___ _/ /____    |
|    \__ \/ _ \/ ___/ | / / _ \/ ___/  / / / / __ \/ __  / __ `/ __/ _ \   |
|   ___/ /  __/ /   | |/ /  __/ /     / /_/ / /_/ / /_/ / /_/ / /_/  __/   |
|  /____/\___/_/    |___/\___/_/      \____/ .___/\__,_/\__,_/\__/\___/    |
|                                         /_/                              |''')
    output("+==========================================================================+")
    output("\n[PaperMC Server Updater]")
    output("[Handles the checking, downloading, and installation of server versions]")
    output("[Written by: Owen Cochell]\n")

    serv = ServerUpdater(args.path, config_file=args.config_file, config=args.no_load_config, prompt=args.interactive,
                         version=args.iv, build=args.ib)

    update_available = True

    # Checking if we are skipping the update

    if not args.no_check:

        # Allowed to check for update:

        update_available = serv.check()

    # Checking if we can install:

    if not args.check_only and update_available:

        # Allowed to install/Can install

        serv.get_new(default_version=args.version, default_build=args.build)
