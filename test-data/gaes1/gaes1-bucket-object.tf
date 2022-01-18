resource "google_storage_bucket_object" "hello_world" {
  name   = "hello_world.zip"
  source = "hello_world.zip"
  bucket = "gaes1-bucket"
}
