resource "google_org_policy_policy" "disable_serial_port_access" {
  name   = "${data.google_folder.parent.name}/policies/compute.disableSerialPortAccess"
  parent = data.google_folder.parent.name
  spec {
    rules {
      enforce = "TRUE"
    }
  }
}
