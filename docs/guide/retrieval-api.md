# Retrieval API

The reviewed HTTP contract is [`api/openapi.yaml`](../../api/openapi.yaml). It is stored as JSON-compatible YAML to avoid emitter-specific changes. The running service exposes `/openapi.json`, `/docs`, and `/redoc`. A software release publishes the contract; consumers pin a release, not a moving branch. Request/response shapes, validation and non-disclosure are tested against the extracted source implementation.

The API uses `/v1`. It exposes document issuer/designation lookup, work-oriented document search, document details/edges/validity/rights/segments/work structure and free graph export. `/v1/export` is not the database-release download endpoint. Consult the schema for required jurisdiction parameters, field types and response codes.

`GET /v1/documents/search` combines exact/text matching and semantic candidates, groups editions by work, ranks the text tier ahead of semantic candidates, and supports issuer filtering and pagination (`limit` 1–100, default 20; nonnegative `offset`). It does not expose independent keyword/semantic mode selectors or global chunk similarity. Ranking may change between knowledge releases without changing the contract, but rights filtering and response shapes must not.

Missing and jurisdiction-invisible documents are indistinguishable (404). A visible document can still have no citable segments; inspect its rights response. Free export uses the existing rights gate, not caller assertions. Validation failures use the existing 400 convention, unavailable storage returns 503, and rate limiting returns 429. The limiter permits 300 requests per fixed one-minute bucket and retains spent buckets for ten minutes, including requests ending in 404.

The service's forwarded-header trust assumes a trusted reverse proxy is its only ingress. Never expose it directly to untrusted callers while trusting their forwarded headers. Keep database access private.

Query and passage embeddings use the same pinned e5 model and separate `query:` / `passage:` prefixes. Set `NORMLY_EMBEDDING_MODEL_PATH` to prepared local weights; there is no runtime download fallback. Retrieval needs the embedding runtime but never Docling. Compatibility of the imported release and runtime model must be verified before readiness.

Breaking HTTP changes need a new API major. Additive changes must update the reviewed contract and tests explicitly. Passage-search/batch/notification additions requested by the web application cutover are separate approval gates, not silently supplied by document search.
