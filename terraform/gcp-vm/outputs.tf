output "control_plane_internal_ip" {
  value = google_compute_instance.control_plane.network_interface[0].network_ip
}

output "control_plane_external_ip" {
  value = google_compute_instance.control_plane.network_interface[0].access_config[0].nat_ip
}

output "worker_01_internal_ip" {
  value = google_compute_instance.worker_01.network_interface[0].network_ip
}

output "worker_01_external_ip" {
  value = google_compute_instance.worker_01.network_interface[0].access_config[0].nat_ip
}
