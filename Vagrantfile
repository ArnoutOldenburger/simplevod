VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "centos6"
  config.vm.network :forwarded_port, guest: 80, host: 8090
  config.vm.provision "shell", path: "deploy-centos.sh"
end
