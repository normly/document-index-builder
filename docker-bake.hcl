variable "REGISTRY" { default = "" }
variable "TAGS" { default = "dev" }
variable "PUSH" { default = "0" }
variable "SOURCE_COMMIT" { default = "development" }

group "default" {
  targets = ["builder", "retrieval"]
}
target "_common" {
  labels = {
    "org.opencontainers.image.source" = "https://github.com/normly/document-index-builder"
    "org.opencontainers.image.licenses" = "AGPL-3.0-or-later"
    "org.opencontainers.image.revision" = SOURCE_COMMIT
  }
  attest = PUSH == "1" ? ["type=provenance,mode=max", "type=sbom"] : []
  args = { SOURCE_COMMIT = SOURCE_COMMIT }
}
target "builder" {
  inherits = ["_common"]
  context = "."
  dockerfile = "docker/python.Dockerfile"
  target = "builder"
  tags = REGISTRY == "" ? ["normly/document-index-builder:dev"] : [for tag in split(" ", TAGS) : "${REGISTRY}/builder:${tag}"]
}
target "retrieval" {
  inherits = ["_common"]
  context = "."
  dockerfile = "docker/python.Dockerfile"
  target = "retrieval"
  tags = REGISTRY == "" ? ["normly/document-index-retrieval:dev"] : [for tag in split(" ", TAGS) : "${REGISTRY}/retrieval:${tag}"]
}
