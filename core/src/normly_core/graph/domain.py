# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

from __future__ import annotations

import uuid

from collections.abc import Callable, Iterator, Mapping

from dataclasses import dataclass

from datetime import date, datetime

from enum import Enum

from typing import Any, Protocol

class LegalBasisCategory(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class TdmOptOutResult(str, Enum):
    NONE_FOUND = "none_found"
    OPT_OUT_PRESENT = "opt_out_present"

class EdgeType(str, Enum):
    REFERENCES = "references"
    REPLACES = "replaces"
    WITHDRAWN_BY = "withdrawn_by"
    BASED_ON_LAW = "based_on_law"
    ADOPTED_FROM = "adopted_from"

class Layer(str, Enum):
    FREE = "free"
    COMMERCIAL = "commercial"

class WithdrawnDeliveryError(Exception):
    """
    Raised when an artifact would be created or updated on a delivery that is
    withdrawn or unknown.

    Without this guard a repeat ingestion run — which the idempotency rule
    requires to be safe — would re-create artifacts a publisher's withdrawal
    had just locked, and `classify()` would clear `revoked_at` outright. The
    withdrawal commitment depends on this staying closed.
    """

    def __init__(self, delivery_id: uuid.UUID):
        self.delivery_id = delivery_id
        super().__init__(f"delivery {delivery_id} is withdrawn or does not exist")

@dataclass(frozen=True)
class Source:
    id: uuid.UUID
    publisher: str
    retrieval_path: str
    legal_basis_category: LegalBasisCategory
    jurisdiction: str
    reviewed_at: date
    responsible_person: str
    commercial_catalog: bool
    contract_reference: str | None
    tdm_opt_out_checked_at: date | None
    tdm_opt_out_result: TdmOptOutResult | None

@dataclass(frozen=True)
class Delivery:
    id: uuid.UUID
    source_id: uuid.UUID
    content_hash: str
    ingested_at: datetime
    withdrawn_at: datetime | None

@dataclass(frozen=True)
class Document:
    id: uuid.UUID
    origin_issuer: str
    origin_number: str
    edition: str
    part: str | None
    work_id: uuid.UUID
    created_via_delivery_id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None = None

@dataclass(frozen=True)
class DocumentDesignation:
    id: uuid.UUID
    document_id: uuid.UUID
    issuer: str
    designation: str
    language: str
    # If an adapter sets this, it MUST be a lexicographically-sortable
    # string whose sort order matches real chronological order (e.g.
    # ISO-8601 "YYYY-MM-DD", the only format any adapter emits today --
    # see the DGUV adapter's _normalise_issue_date()). This field is
    # compared with a plain `<` in
    # PostgresDocumentRepository.find_previous_edition (repositories.py) --
    # a non-sortable format there would silently produce a wrong result,
    # not an error.
    edition: str | None
    is_primary: bool
    delivery_id: uuid.UUID

@dataclass(frozen=True)
class DocumentTitle:
    id: uuid.UUID
    document_id: uuid.UUID
    language: str
    title: str
    delivery_id: uuid.UUID

@dataclass(frozen=True)
class Edge:
    id: uuid.UUID
    from_document_id: uuid.UUID
    to_document_id: uuid.UUID
    edge_type: EdgeType
    jurisdiction: str | None
    layer: Layer
    delivery_id: uuid.UUID
    revoked_at: datetime | None
    created_at: datetime

@dataclass(frozen=True)
class RightsClassification:
    document_id: uuid.UUID
    jurisdiction: str
    may_process: bool
    may_index_fulltext: bool
    may_cite_passages: bool
    may_export_free: bool
    legal_basis_reference: str
    classified_at: datetime
    classified_by: str
    delivery_id: uuid.UUID
    revoked_at: datetime | None

@dataclass(frozen=True)
class WorkStructureEntry:
    document_id: uuid.UUID
    origin_issuer: str
    origin_number: str
    edition: str
    designation: str | None
    status: str

@dataclass(frozen=True)
class WorkStructure:
    work_id: uuid.UUID
    editions: list[WorkStructureEntry]
    national_adoptions: list[WorkStructureEntry]

class SourceRepository(Protocol):
    def create_source(
        self,
        *,
        publisher: str,
        retrieval_path: str,
        legal_basis_category: LegalBasisCategory,
        jurisdiction: str,
        reviewed_at: date,
        responsible_person: str,
        commercial_catalog: bool = False,
        contract_reference: str | None = None,
        tdm_opt_out_checked_at: date | None = None,
        tdm_opt_out_result: TdmOptOutResult | None = None,
    ) -> Source: ...

    def get_source(self, source_id: uuid.UUID) -> Source | None: ...

    def find_by_publisher(self, publisher: str) -> Source | None: ...

class DeliveryRepository(Protocol):
    def record_delivery(
        self, *, source_id: uuid.UUID, content_hash: str, ingested_at: datetime
    ) -> Delivery: ...

    def get_delivery(self, delivery_id: uuid.UUID) -> Delivery | None: ...

    def find_delivery(self, source_id: uuid.UUID, content_hash: str) -> Delivery | None: ...

    def revoke_delivery(self, delivery_id: uuid.UUID) -> None: ...

class DocumentRepository(Protocol):
    """
    The rights-gated read and write surface for document nodes.

    Every read declared here takes a jurisdiction and filters through
    `rights_classification`; there is deliberately no method that returns
    documents unfiltered.

    `PostgresDocumentRepository` additionally carries six ungated methods
    that are **not** part of this Protocol and must not be treated as
    content-serving API: `get_document_unchecked` (existence check for
    pipeline and administrative use, e.g. proving a document node survived a
    delivery revocation), `list_documents_for_work_unchecked` (every Document
    for a Work, regardless of jurisdiction or rights classification —
    notify-watchers, Task 6; batch variants `documents_for_works_unchecked` and
    `documents_by_ids_unchecked` serve the personal-data export and return
    identifiers only), `list_designations` and `list_titles` (identity
    resolution and pipeline metadata — designations are the identity of a node
    across national adoptions, independent of any rights question). They are
    internal implementation methods.

    Exception: `get_document_unchecked` may be invoked by a public-facing read
    path only as a pure existence check—to decide 404 vs. content, e.g.
    distinguishing "no such document" from "document exists but has no visible
    content in this jurisdiction"—provided its result is never exposed in a
    response body or used to reveal anything about rights-gated content.

    Any public-facing read path — the API sub-project above all — MUST use
    `get_document_for_jurisdiction` / `list_documents_for_jurisdiction`.
    """

    def create_document(
        self,
        *,
        origin_issuer: str,
        origin_number: str,
        edition: str,
        part: str | None,
        delivery_id: uuid.UUID,
        work_id: uuid.UUID | None = None,
    ) -> Document:
        """
        `work_id` is the pipeline's explicit assignment when an ingestion
        signal (REPLACES/WITHDRAWN_BY/ADOPTED_FROM to a known document)
        resolved one -- see `normly_core.pipeline.work_assignment`. Omitted,
        the repository creates a fresh 1:1 Work for this document, which is
        the correct default whenever nothing links it to an existing one.
        """
        ...

    def add_designation(
        self,
        *,
        document_id: uuid.UUID,
        issuer: str,
        designation: str,
        language: str,
        edition: str | None,
        is_primary: bool,
        delivery_id: uuid.UUID,
    ) -> DocumentDesignation: ...

    def add_title(
        self, *, document_id: uuid.UUID, language: str, title: str, delivery_id: uuid.UUID
    ) -> DocumentTitle: ...

    def get_document_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> Document | None: ...

    def list_documents_for_jurisdiction(self, jurisdiction: str) -> list[Document]: ...

    def search_documents_for_jurisdiction(
        self, jurisdiction: str, *, q: str | None = None, issuer: str | None = None,
        limit: int = 20, offset: int = 0,
    ) -> tuple[list[Document], int]:
        """
        Free-text (designation/title, case-insensitive substring) and/or
        issuer-filtered listing, paginated. Returns (page, total_matching) --
        `total` reflects the full filtered set, not just this page's length.
        An empty q and issuer returns the whole jurisdiction, paginated --
        this is also how "browse by issuer" and "browse everything" work,
        without a separate method.
        """
        ...

    def search_works_for_jurisdiction(
        self, jurisdiction: str, *, q: str | None = None, issuer: str | None = None,
        query_vector: list[float] | None = None, embedding_model_name: str | None = None,
        limit: int = 20, offset: int = 0,
    ) -> tuple[list[WorkSearchHit], int]:
        """
        Hybrid, Work-grouped search: exact ILIKE matches on designation/title
        (Tier 1, via search_documents_for_jurisdiction) rank first, then
        documents ranked by cosine distance to `query_vector` (Tier 2) fill
        the rest. Both tiers are deduplicated by work_id -- exactly one hit
        per Work, led by its best-ranked Document. `total` counts distinct
        Works matched, not raw document rows.

        `query_vector` must already be computed (via
        `EmbeddingModel.embed_query`) by the caller -- this repository never
        calls the embedding model itself. `embedding_model_name` is required
        whenever `query_vector` is given (mixing vectors from different
        models in one ORDER BY compares distances from unrelated vector
        spaces); if either is omitted, Tier 2 is skipped and this behaves as
        Tier-1-only, Work-grouped search.
        """
        ...

    def list_exportable_documents_for_jurisdiction(self, jurisdiction: str) -> list[Document]:
        """
        Stricter than `list_documents_for_jurisdiction`: additionally requires
        `may_export_free=True`. A document may be processable/servable in a
        jurisdiction (`may_process=True`) without being licensed for
        redistribution in the public free-tier export — e.g. content received
        under a contract that permits internal processing but not
        republication. This is the correct method for any public/free-tier
        export or dump; never for internal/authenticated content-serving
        reads, which should keep using `get_document_for_jurisdiction` /
        `list_documents_for_jurisdiction`.
        """
        ...

    def find_by_designation(
        self, issuer: str, designation: str, edition: str | None = None
    ) -> Document | None: ...

    def find_previous_edition(
        self, issuer: str, designation: str, before_edition: str
    ) -> Document | None:
        """
        The edition immediately preceding `before_edition` for this
        (issuer, designation) -- the greatest `edition` value strictly less
        than `before_edition` among that designation's other documents, or
        None if none exists (including when `before_edition` is itself the
        oldest known edition).

        Unlike `find_by_designation`'s edition-less fallback (which answers
        "most recently INSERTED"), this answers "the true predecessor in
        edition order" -- out-of-order ingestion (an older archive edition
        arriving after its newer successor is already known) or same-
        transaction batches (where created_at ties are common) must not
        produce an inverted or nondeterministic REPLACES edge.
        """
        ...

class RateLimitRepository(Protocol):
    """
    A generic, jurisdiction-independent request counter used to enforce
    REQ-ACC-003's anonymous quota. Not part of the graph model, but kept in
    the same repository layer as everything else that touches the database,
    per AGENTS.md's "Database access only through the repository layer".
    """

    def record_and_check(
        self, *, key: str, window_start: datetime, limit: int
    ) -> bool:
        """
        Atomically increments the request counter for `key` within the
        window starting at `window_start`, and reports whether the caller
        is still within `limit`. Returns True when the request should be
        allowed (count <= limit after incrementing), False when it should
        be rejected.
        """
        ...

class RightsRepository(Protocol):
    def classify(
        self,
        *,
        document_id: uuid.UUID,
        jurisdiction: str,
        may_process: bool,
        may_index_fulltext: bool,
        may_cite_passages: bool,
        may_export_free: bool,
        legal_basis_reference: str,
        classified_at: datetime,
        classified_by: str,
        delivery_id: uuid.UUID,
    ) -> RightsClassification: ...

    def get_classification(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> RightsClassification | None: ...

class EdgeRepository(Protocol):
    def create_edge(
        self,
        *,
        from_document_id: uuid.UUID,
        to_document_id: uuid.UUID,
        edge_type: EdgeType,
        jurisdiction: str | None,
        layer: Layer,
        delivery_id: uuid.UUID,
    ) -> Edge: ...

    def list_edges_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Edge]:
        """
        Outgoing edges (document_id == from_document_id), rights-gated on BOTH
        endpoints (may_process, unrevoked, matching jurisdiction) and nothing
        else. In particular this applies NO layer filter: COMMERCIAL-layer
        edges are returned.

        Callers in this repository: pipeline and processing code only. No HTTP
        endpoint may call this -- a public, anonymous caller would receive
        commercial-tier relationships. Public read paths use
        `list_free_layer_edges_for_jurisdiction`; the bulk export uses
        `list_exportable_edges_for_jurisdiction`.
        """
        ...

    def list_incoming_edges_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Edge]:
        """
        Incoming edges (document_id == to_document_id) -- e.g. the
        REPLACES/WITHDRAWN_BY edges a successor or withdrawal-notice document
        points at document_id. Same dual rights-gating as
        `list_edges_for_jurisdiction`, direction reversed, and likewise NO
        layer filter: COMMERCIAL-layer edges are returned.

        Callers in this repository: pipeline and processing code only. No HTTP
        endpoint may call this; the public validity endpoint uses
        `list_free_layer_incoming_edges_for_jurisdiction`.
        """
        ...

    def list_free_layer_edges_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Edge]:
        """
        `list_edges_for_jurisdiction` plus `layer == Layer.FREE`. Nothing else
        differs: same outgoing direction, same dual may_process gating, same
        ordering.

        This is the method for public, anonymous read paths that must not
        disclose commercial-tier relationships (REQ-GRAPH-002 reserves
        section-level references within licensed norms for the paid tier). It
        is deliberately NOT the bulk-export case: it does not require
        `may_export_free`, because "may this specific relationship be shown to
        a free-tier caller" is a narrower question than "is this document
        flagged for inclusion in the bulk dump". A document that is
        may_process=True but may_export_free=False still answers questions
        about itself over the API; it just does not appear in `/v1/export`.

        Caller in this repository: GET /v1/documents/{id}/edges.
        """
        ...

    def list_free_layer_incoming_edges_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Edge]:
        """
        `list_incoming_edges_for_jurisdiction` plus `layer == Layer.FREE`.
        Incoming direction (document_id == to_document_id), otherwise the same
        relationship to its sibling as
        `list_free_layer_edges_for_jurisdiction` has to
        `list_edges_for_jurisdiction` -- see there for why this is distinct
        from the `may_export_free`-gated export methods.

        Caller in this repository: GET /v1/documents/{id}/validity.
        """
        ...

    def list_exportable_edges_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Edge]:
        """
        `list_edges_for_jurisdiction` plus `layer == Layer.FREE` plus
        `may_export_free` on BOTH endpoints. The strictest of the four
        listings, and the only one that consults `may_export_free`.

        This is the bulk free-tier dump gate, not general public visibility:
        an endpoint answering about one document should use
        `list_free_layer_edges_for_jurisdiction` instead, which does not
        require the export flag.

        Caller in this repository: GET /v1/export.
        """
        ...

    def get_work_structure_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> WorkStructure | None:
        """
        None if `document_id` is not visible in `jurisdiction` (same gate as
        get_document_for_jurisdiction). Otherwise: every Document sharing this
        document's work_id and visible in this jurisdiction, split into two
        lists by edge type among a BOUNDED set (this Work's documents and the
        edges between them only -- not an unbounded graph traversal, matches
        ADR-006's "graph queries stay shallow"):

        `editions` -- every Work member connected to `document_id` via a path
        of ONLY REPLACES/WITHDRAWN_BY edges (same-lineage chain, typically one
        issuer), including `document_id` itself -- UNLESS `document_id` is
        the only visible Work member, in which case both lists are empty
        (nothing to list itself against).

        `national_adoptions` -- every OTHER Work member (not in the editions
        chain). Together the two lists cover every visible Work member
        exactly once (or are both empty in the single-member case above).

        Each entry's `status` is computed the same way GET .../validity
        computes it for a single document: an entry with an incoming
        REPLACES edge (within this bounded edge set) is "replaced", an
        incoming WITHDRAWN_BY edge is "withdrawn", otherwise "valid".
        """
        ...

@dataclass(frozen=True)
class Segment:
    id: uuid.UUID
    document_id: uuid.UUID
    delivery_id: uuid.UUID
    sequence_number: int
    heading: str | None
    text: str
    language: str
    created_at: datetime

class SegmentRepository(Protocol):
    def add_segment(
        self,
        *,
        document_id: uuid.UUID,
        delivery_id: uuid.UUID,
        sequence_number: int,
        heading: str | None,
        text: str,
        language: str,
    ) -> tuple[Segment, bool]:
        """
        Store one segment; return it together with whether this call created it.

        The flag is what keeps a run summary honest: on the idempotent path the
        segment comes back unchanged and nothing was created.
        """
        ...

    def list_segments_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Segment]: ...

    def list_citable_segments_for_jurisdiction(
        self, document_id: uuid.UUID, jurisdiction: str
    ) -> list[Segment]:
        """Segments whose text may be shown to a reader (may_cite_passages)."""
        ...

    def list_segment_headings_for_jurisdiction(
        self, segment_ids: list[uuid.UUID], jurisdiction: str
    ) -> dict[uuid.UUID, str | None]:
        """Headings of the visible segments among segment_ids; others are absent."""
        ...

    def find_similar_segments_for_jurisdiction(
        self, query_vector: list[float], jurisdiction: str, model_name: str, limit: int = 5,
    ) -> list[Segment]: ...

@dataclass(frozen=True)
class Embedding:
    id: uuid.UUID
    segment_id: uuid.UUID
    delivery_id: uuid.UUID
    model_name: str
    vector: list[float]
    created_at: datetime

class EmbeddingRepository(Protocol):
    """
    The write surface for segment embeddings.

    `PostgresEmbeddingRepository` additionally carries `get_embedding_unchecked`,
    which is **not** part of this Protocol: it takes no jurisdiction and joins no
    rights classification, so it is a pipeline and administrative method, never a
    content-serving read — the same split `DocumentRepository` documents for
    `get_document_unchecked`.
    """

    def add_embedding(
        self,
        *,
        segment_id: uuid.UUID,
        delivery_id: uuid.UUID,
        model_name: str,
        vector: list[float],
    ) -> tuple[Embedding, bool]:
        """Store one embedding; return it and whether this call created it."""
        ...

@dataclass(frozen=True)
class DocumentEmbedding:
    id: uuid.UUID
    document_id: uuid.UUID
    model_name: str
    vector: list[float]
    delivery_id: uuid.UUID
    created_at: datetime

class DocumentEmbeddingRepository(Protocol):
    """
    The write surface for per-Document search embeddings.

    Unlike `EmbeddingRepository.add_embedding` (segment-scoped, create-if-
    absent -- segment text never changes, so no update is ever needed),
    `upsert_document_embedding` always (re)writes the vector: a Document's
    primary designation/title can change across re-ingestion, so the
    embedding must track it rather than freeze on the first value ever seen.
    """

    def upsert_document_embedding(
        self,
        *,
        document_id: uuid.UUID,
        delivery_id: uuid.UUID,
        model_name: str,
        vector: list[float],
    ) -> DocumentEmbedding: ...

    def list_documents_without_embedding(self, model_name: str) -> list[Document]:
        """
        Every Document with no DocumentEmbedding row for `model_name` yet.
        Pipeline/administrative method (used by the `backfill-document-
        embeddings` CLI command) -- nothing here is served to a public
        caller, it only decides what the backfill still has to do.
        """
        ...

@dataclass(frozen=True)
class WorkSearchHit:
    work_id: uuid.UUID
    best_match: Document
    other_editions_count: int

class WorkStatus(str, Enum):
    ACTIVE = "active"
    MERGED = "merged"

class WorkCreatedVia(str, Enum):
    AUTO_MATCHED = "auto_matched"
    MANUAL = "manual"

@dataclass(frozen=True)
class Work:
    id: uuid.UUID
    status: WorkStatus
    merged_into_work_id: uuid.UUID | None
    created_via: WorkCreatedVia
    created_at: datetime

class WorkRepository(Protocol):
    def create_work(self, *, created_via: WorkCreatedVia) -> Work: ...

    def get_work(self, work_id: uuid.UUID) -> Work | None:
        """
        Look up a Work by id. If it has been merged into another Work
        (`status == MERGED`), returns the target Work it was merged into
        instead -- callers never see a retired Work as if it were current.
        """
        ...

class ContradictoryWorkMergeError(Exception):
    def __init__(self, source_work_id: uuid.UUID, target_work_id: uuid.UUID):
        self.source_work_id = source_work_id
        self.target_work_id = target_work_id
        super().__init__(
            f"cannot merge work {source_work_id} into {target_work_id}: "
            "same work, or target is not active"
        )

class IdentityResolutionStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"

class IdentityResolutionCaseType(str, Enum):
    NEW_DOCUMENT = "new_document"
    WORK_MERGE = "work_merge"

@dataclass(frozen=True)
class IdentityResolutionCase:
    id: uuid.UUID
    delivery_id: uuid.UUID
    case_type: IdentityResolutionCaseType
    raw_designation: str | None
    raw_issuer: str | None
    reason: str
    status: IdentityResolutionStatus
    resolved_document_id: uuid.UUID | None
    source_work_id: uuid.UUID | None
    target_work_id: uuid.UUID | None
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime

class IdentityResolutionRepository(Protocol):
    def enqueue_case(
        self,
        *,
        delivery_id: uuid.UUID,
        raw_designation: str,
        raw_issuer: str | None,
        reason: str,
    ) -> IdentityResolutionCase: ...

    def enqueue_work_merge_case(
        self,
        *,
        delivery_id: uuid.UUID,
        source_work_id: uuid.UUID,
        target_work_id: uuid.UUID,
        reason: str,
    ) -> IdentityResolutionCase: ...

    def list_pending_cases(self) -> list[IdentityResolutionCase]: ...

    def resolve_case(
        self, case_id: uuid.UUID, *, resolved_document_id: uuid.UUID, resolved_by: str
    ) -> IdentityResolutionCase: ...

    def resolve_work_merge_case(
        self, case_id: uuid.UUID, *, resolved_by: str
    ) -> IdentityResolutionCase:
        """
        Reassign every Document.work_id from the case's source_work_id to its
        target_work_id, mark the source Work MERGED, and mark the case
        RESOLVED. Raises ContradictoryWorkMergeError -- writing nothing -- if
        source_work_id == target_work_id or the target Work is not ACTIVE
        (already merged elsewhere).
        """
        ...

    def reject_case(
        self, case_id: uuid.UUID, *, resolved_by: str
    ) -> IdentityResolutionCase: ...

@dataclass(frozen=True)
class ExchangeColumn:
    name: str
    kind: str  # "string"|"bool"|"int"|"float"|"timestamp"|"date"|"vector"

@dataclass(frozen=True)
class ImportRecord:
    dump_version: str
    exchange_schema_version: int
    embedding_model_revision: str
    imported_at: datetime

class ImportBlockedError(Exception):
    """
    Last guard of the import (ADR-026): a statement hit a foreign key nobody
    anticipated. User data no longer blocks an import -- missing identifier
    rows become tombstones and citations of purged segments are detached --
    so this signals a table that is missing from the import classes. Nothing
    is changed once the caller has rolled back (or used a savepoint): the
    methods never commit, and the transaction is left in a failed state.
    """

    def __init__(self, step: str, detail: str):
        super().__init__(f"import blocked at step {step}: {detail}")
        self.step = step
        self.detail = detail

RowBatches = Callable[[], Iterator[list[dict[str, Any]]]]

class KnowledgeExchangeRepository(Protocol):
    """
    Bulk access to the free knowledge base for the versioned dump (ADR-025).

    Deliberately no `get_`/`list_` names: those prefixes trigger the
    jurisdiction guard in test_architecture.py, and the export gate here is
    the rights classification itself (may_process AND may_export_free, not
    revoked, delivery not withdrawn, source category A/B/D and not a
    commercial catalogue), evaluated across all jurisdictions.

    Exported rows never carry personal names: `source.responsible_person` and
    `rights_classification.classified_by` are replaced by the constant role
    label `PUBLISHED_ROLE` ("normly maintainers"). The names stay in the local
    ingestion database; an import overwrites them with the label.
    """

    def exchange_columns(self, table: str) -> list[ExchangeColumn]: ...

    def iter_exportable_rows(
        self, table: str, *, batch_size: int = 5000
    ) -> Iterator[list[dict[str, Any]]]: ...

    def exportable_deliveries(self) -> list[tuple[str, str, str]]: ...

    def replace_knowledge_base(
        self, tables: Mapping[str, RowBatches], *, record: ImportRecord
    ) -> None:
        """
        Replace the knowledge base with the dump; a takedown always wins.
        Content missing from the dump is deleted, missing identifier rows
        (work, document, edge) are kept with `retired_at`, a missing delivery
        gets `withdrawn_at`. User data never blocks the import; only an
        unexpected foreign key raises ImportBlockedError. Never commits.
        """
        ...

    def has_documents(self) -> bool:
        """True when the database holds at least one document (retired or not)."""
        ...

    def export_tombstone_support(self) -> dict[str, list[dict[str, Any]]]:
        """
        All retired identifier rows (work, document, edge) plus their foreign-key
        parents among source, delivery, work, document, edge, with every column
        (also retired_at / revoked_at), per table sorted by primary key. Never
        content, never user data. Used by the backup so a rollback can restore
        the identifiers that no dump contains (ADR-026).
        """
        ...

    def restore_tombstone_support(
        self, rows: Mapping[str, list[dict[str, Any]]], *, restored_at: datetime
    ) -> None:
        """
        Insert the rows in foreign-key order, never changing an existing row.
        Inserted identifier rows without `retired_at` get `restored_at`, so they
        count as retired. Never commits.
        """
        ...

    def imported_version(self) -> ImportRecord | None: ...
