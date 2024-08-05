import os
import argparse
import sys
import time
import warnings
import yaml

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import paramiko


def load_yaml(yaml_file: str = None):
        with open(f"servers/{yaml_file}", 'r') as f:
            config = yaml.safe_load(f)
        return config


class JankyInit():

    def __init__(self, config):
        self.config = config
        self.sleep = 1.5


    def _ssh_client_connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.load_system_host_keys() 
        self.client.connect(hostname=self.config['ip'], username=self.config['user'], password=self.config['user-pw'], timeout=5)

    def _run_command(self, command):
        self._ssh_client_connect()
        full_command = f"sudo -S -p '' {command}"
        print(full_command)
        stdin, stdout, stderr = self.client.exec_command(full_command)
        stdin.write(self.config['user-pw'] + "\n")
        stdin.flush()



        if "ufw enable" in command:
            stdin.write("y" + "\n")
            stdin.flush()

        while not stdout.channel.exit_status_ready():
            err = stderr.readlines() 
            if len(err) > 0: 
                print(err)

            if stdout.channel.recv_ready():
                print(stdout.channel.recv(9999).decode().strip())



        time.sleep(self.sleep)

    def update_os(self):
        commands = ["apt-get update",
                    "apt-get upgrade -y"]
        
        for command in commands:
            self._run_command(command)


    def install_apps(self):
        package_string = " ".join(self.config['software'])

        self._run_command(f"apt-get install {package_string} -y")

        if "ufw" in package_string:
            commands = ["ufw allow 22/tcp",
                        "sed -i 's/IPV6=yes/IPV6=no/g' /etc/default/ufw",
                        "ufw enable",
                        "ufw reload",
                        "ufw status"
            ]

            for command in commands:
                self._run_command(command)


    def setup_ssh_keys(self):
        ssh_key_location = f"{os.getcwd()}/ssh_keys"
        keys = []
        for _ in self.config['ssh_keys']:
            with open(f"{ssh_key_location}/{_}", "r") as key:
                keys.append(key.read())

        # convert to for loop with list of commands
        commands = ["mkdir .ssh",
                    f"chown -R {self.config["user"]}:{self.config["user"]} .ssh",
                    f"echo '{"".join(keys)}' >> .ssh/authorized_keys",
                    "chmod 600 .ssh/authorized_keys",
                    "chmod 700 .ssh", 
                    "sed -i '/PubkeyAuthentication/s/^#//' /etc/ssh/sshd_config",
                    "sed -i '/AuthorizedKeysFile/s/^#//' /etc/ssh/sshd_config",
                    "sed -i 's/#PasswordAuthentication\\syes/PasswordAuthentication no/g' /etc/ssh/sshd_config",
                    "systemctl restart sshd"
        ]

        for command in commands:
            self._run_command(command)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", help="yaml file location (defaults to servers folder)")
    args = parser.parse_args()
    parser.parse_args(args=None if sys.argv[1:] else ['--help'])

    config = load_yaml(args.yaml)
    print(config)

    init = JankyInit(config=config)
    init.update_os()
    init.install_apps()
    init.setup_ssh_keys()