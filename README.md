# NVM Panel

A lightweight VM/LXC hosting control panel for Ubuntu/Debian VMs.

- Runs on port **6767**
- Default admin: **admin / admin123**
- Local node is created automatically
- Admin can add remote nodes, create users, create LXC/KVM servers, and upload logo/background
- Users get: Console, File Manager, Forward Port (pinggy.io), Subusers
- KVM servers additionally show **Reboot**

## Install
```bash
unzip nvm-panel.zip
cd nvm-panel
bash setup.sh
```

Open: http://YOUR_VM_IP:6767

## Notes
- LXC actions use `lxc-start`, `lxc-stop`; KVM actions use `virsh`.
- Install on the host: `apt install -y lxc libvirt-clients qemu-kvm`
- Change the Flask secret key in `app.py` before production use.
