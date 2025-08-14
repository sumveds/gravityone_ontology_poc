from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.generation import GraphRAG
from config.settings import settings

import signal
import sys
import threading
import time

# =========================
# CONFIG
# =========================
LABELS = [
    "Organisation", "OrganisationGroup", "BusinessUnit", "Owner", "BusinessPlan",
    "StrategicObjective", "StrategicOutcome", "Objective", "KPI", "Risk",
    "Output", "Project", "Capability", "Budget"
]
INDEX_NAME = "embedding_index"
EMBED_MODEL = "text-embedding-3-small"  # 1536 dims
EMBED_DIMS = 1536

# General, schema-aware guidance (prepended to user queries)
GRAPH_ANALYST_INSTRUCTION = (
    "You are an enterprise strategy consultant / analyst. Use ONLY the retrieved graph facts "
    "to answer questions across all entities and relationships (Organisation, OrganisationGroup, "
    "BusinessUnit, Owner, BusinessPlan, StrategicObjective, StrategicOutcome, Objective, KPI, Risk, "
    "Output, Project, Capability, Budget). Prefer precise, structured answers. When useful, show brief "
    "tables or bullet lists.\n\n"
    "Rules:\n"
    "1) Do not invent entities, attributes, numbers, or links that are not in the retrieved facts.\n"
    "2) If the question requires a comparison or ranking, use the numeric fields present (e.g., current_value, target, threshold).\n"
    "3) For KPI/metric status, apply direction-aware logic when fields exist:\n"
    "   - If direction='up': On Track if current>=target; Off Track if current<threshold; else At Risk.\n"
    "   - If direction='down': On Track if current<=target; Off Track if current>threshold; else At Risk.\n"
    "4) For BusinessUnit health (when a KPI named 'Health Score' is present):\n"
    "   - Healthy if current_value >= target; Not Healthy if current_value < threshold; else At Risk.\n"
    "5) If information is insufficient, state what is missing rather than guessing.\n"
    # "6) When relationships matter, reference them succinctly like: A -[:RELTYPE]-> B.\n"
    # "7) Keep responses concise and business-friendly."
    "6) Keep responses in natural language, concise and business-friendly."
)

# =========================
# CLIENTS
# =========================
# Use secure scheme (neo4j+s:// or bolt+s://) for Aura / TLS
driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    connection_timeout=30,          # seconds
    max_connection_lifetime=300     # seconds
)

embedder = OpenAIEmbeddings(model=EMBED_MODEL, api_key=settings.OPENAI_API_KEY)

# Lower temperature for deterministic numeric reasoning
llm = OpenAILLM(
    model_name="gpt-5-mini",
    system_message=GRAPH_ANALYST_INSTRUCTION,
    model_params={"temperature": 1},
    api_key=settings.OPENAI_API_KEY
)

# =========================
# UTIL
# =========================
class Spinner:
    def __init__(self, message="Processing"):
        self.message = message
        self.spinner_chars = "|/-\\"
        self.idx = 0
        self.stop_spinner = False
        self.spinner_thread = None

    def spin(self):
        while not self.stop_spinner:
            print(f"\r{self.message} {self.spinner_chars[self.idx % len(self.spinner_chars)]}", end="", flush=True)
            self.idx += 1
            time.sleep(0.1)

    def start(self):
        self.stop_spinner = False
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.start()

    def stop(self):
        self.stop_spinner = True
        if self.spinner_thread:
            self.spinner_thread.join()
        print("\r" + " " * (len(self.message) + 10) + "\r", end="", flush=True)

def signal_handler(sig, frame):
    print("\n\nGracefully shutting down...")
    driver.close()
    sys.exit(0)

# =========================
# SETUP
# =========================
def tag_searchable_nodes():
    """Tag all relevant nodes with :Searchable label."""
    with driver.session() as session:
        session.run("""
            MATCH (n)
            WHERE any(l IN labels(n) WHERE l IN $labels)
            SET n:Searchable
        """, {"labels": LABELS})
    print("✅ Tagged searchable nodes with :Searchable")

def reset_embeddings():
    with driver.session() as session:
        result = session.run("""
            MATCH (n:Searchable)
            WHERE n.embedding IS NOT NULL
            REMOVE n.embedding
            RETURN count(n) AS cleared_count
        """)
        count = result.single()["cleared_count"]
        print(f"🧹 Cleared embeddings from {count} nodes")

def setup_vector_index():
    with driver.session() as session:
        try:
            session.run(f"DROP INDEX {INDEX_NAME} IF EXISTS")
        except Exception:
            pass

        session.run(f"""
            CREATE VECTOR INDEX {INDEX_NAME} IF NOT EXISTS
            FOR (n:Searchable) ON (n.embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {EMBED_DIMS},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
        """)
        print(f"✅ Created/verified vector index '{INDEX_NAME}' for :Searchable")

def build_text_from_node(node_props: dict) -> str:
    """
    Serialize node properties for embedding.
    - 'name' first, then all other scalar props (str/int/float/bool).
    - Skips 'embedding' and None values.
    - Schema-agnostic to keep future attributes in play.
    """
    if not node_props:
        return ""

    fields = []
    name = node_props.get("name")
    if name:
        fields.append(str(name))

    for k, v in node_props.items():
        if k in ("name", "embedding") or v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            fields.append(f"{k}: {v}")

    return " | ".join(fields)

def backfill_embeddings(batch_size: int = 1000):
    """Embed all :Searchable nodes without embeddings in batches until done."""
    with driver.session() as session:
        total = session.run("MATCH (n:Searchable) RETURN count(n) AS c").single()["c"]
        print(f"📦 Total searchable nodes: {total}")

        processed_total = 0
        while True:
            result = session.run("""
                MATCH (n:Searchable)
                WHERE n.embedding IS NULL
                RETURN id(n) AS id, properties(n) AS props
                LIMIT $limit
            """, {"limit": batch_size})

            nodes = list(result)
            if not nodes:
                break

            print(f"🔄 Processing {len(nodes)} nodes for embeddings...")
            with driver.session() as write_sess:
                for i, rec in enumerate(nodes, 1):
                    node_id, props = rec["id"], rec["props"]
                    text = build_text_from_node(props)
                    if not text.strip():
                        continue
                    try:
                        embedding = embedder.embed_query(text)
                        write_sess.run(
                            "MATCH (n) WHERE id(n) = $id SET n.embedding = $embedding",
                            {"id": node_id, "embedding": embedding}
                        )
                    except Exception as e:
                        print(f"    ❌ Error embedding node {node_id}: {e}")

                    if i % 100 == 0:
                        print(f"    ...{i}/{len(nodes)}")

            processed_total += len(nodes)
            print(f"✅ Embedded so far: {processed_total}")

        print("🎉 Embedding backfill complete.")

# =========================
# RETRIEVAL QUERY (uses ANN-bound `node`)
# VectorCypherRetriever binds variables `node` and `score`.
# We preserve `node`, summarize neighbors, and (optionally) compute BU health.
# =========================
RETRIEVAL_QUERY = """
// VectorCypherRetriever binds `node` and `score`.
// 1) Collect neighbors for graph context
WITH node, score
OPTIONAL MATCH (node)-[r]-(m)
WITH node, score,
     collect(DISTINCT {rel: type(r), nbr_label: head(labels(m)), nbr_name: m.name})[0..8] AS neighbors

// 2) KPI-specific: compute status using direction-aware logic
WITH node, score, neighbors,
     (CASE WHEN node:KPI THEN node.current_value END) AS cv,
     (CASE WHEN node:KPI THEN node.target END)        AS tgt,
     (CASE WHEN node:KPI THEN node.threshold END)     AS thr,
     (CASE WHEN node:KPI THEN node.direction END)     AS dir
WITH node, score, neighbors, cv, tgt, thr, dir,
     CASE
       WHEN node:KPI AND cv IS NOT NULL AND tgt IS NOT NULL AND thr IS NOT NULL AND dir IS NOT NULL THEN
         CASE
           WHEN dir = 'up'   AND cv >= tgt THEN 'On Track'
           WHEN dir = 'up'   AND cv <  thr THEN 'Off Track'
           WHEN dir = 'up'                      THEN 'At Risk'
           WHEN dir = 'down' AND cv <= tgt THEN 'On Track'
           WHEN dir = 'down' AND cv >  thr THEN 'Off Track'
           WHEN dir = 'down'                    THEN 'At Risk'
           ELSE NULL
         END
       ELSE NULL
     END AS kpi_status

// 3) Root causes: direct KPI->Risk and indirect Risk->Objective->KPI
OPTIONAL MATCH (node)-[:AFFECTED_BY]->(r1:Risk)
WITH node, score, neighbors, cv, tgt, thr, dir, kpi_status,
     collect(DISTINCT r1.name) AS direct_risks
OPTIONAL MATCH (node)<-[:MEASURED_BY|:TRACKS|:MEASURES]-(o:Objective)<-[:THREATENS]-(r2:Risk)
WITH node, score, neighbors, cv, tgt, thr, dir, kpi_status, direct_risks,
     collect(DISTINCT r2.name) AS obj_risks,
     collect(DISTINCT o.name)[0..5] AS kpi_objectives

// 4) BusinessUnit health from BU Health Score KPI
OPTIONAL MATCH (node)<-[:MEASURES|:TRACKS|:MEASURED_BY]-(bukpi:KPI)
WHERE node:BusinessUnit AND bukpi.name CONTAINS 'Health Score'
WITH node, score, neighbors, cv, tgt, thr, dir, kpi_status, direct_risks, obj_risks, kpi_objectives, bukpi,
     CASE
       WHEN node:BusinessUnit AND bukpi IS NOT NULL THEN
         CASE
           WHEN bukpi.current_value >= bukpi.target THEN 'Healthy'
           WHEN bukpi.current_value <  bukpi.threshold THEN 'Not Healthy'
           ELSE 'At Risk'
         END
       ELSE NULL
     END AS bu_health

// 5) For non-KPI nodes: summarize linked KPI performance counts
OPTIONAL MATCH (node)<-[:MEASURED_BY|:TRACKS|:MEASURES]-(k:KPI)
WITH node, score, neighbors, cv, tgt, thr, dir, kpi_status, direct_risks, obj_risks, kpi_objectives, bu_health, bukpi,
     collect(k) AS linked_kpis
WITH node, score, neighbors, cv, tgt, thr, dir, kpi_status, direct_risks, obj_risks, kpi_objectives, bu_health, bukpi,
     [k IN linked_kpis WHERE (k.direction = 'up'   AND k.current_value <  k.threshold)
                      OR (k.direction = 'down' AND k.current_value >  k.threshold)] AS under_kpis,
     [k IN linked_kpis WHERE (k.direction = 'up'   AND k.current_value >= k.target)
                      OR (k.direction = 'down' AND k.current_value <= k.target)] AS ontrack_kpis

// 6) Render a rich text line the LLM can use directly
WITH node, score, neighbors, cv, tgt, thr, dir, kpi_status, direct_risks, obj_risks, kpi_objectives, bu_health, bukpi, under_kpis, ontrack_kpis,
     // join helper strings without APOC
     reduce(s = '', x IN direct_risks | s + CASE WHEN s='' THEN '' ELSE ', ' END + coalesce(x,'')) AS direct_risks_s,
     reduce(s = '', x IN obj_risks    | s + CASE WHEN s='' THEN '' ELSE ', ' END + coalesce(x,'')) AS obj_risks_s,
     reduce(s = '', x IN kpi_objectives | s + CASE WHEN s='' THEN '' ELSE ', ' END + coalesce(x,'')) AS obj_objs_s,
     reduce(s = '', n IN neighbors | s +
       CASE WHEN s='' THEN '' ELSE '; ' END +
       coalesce(n.rel,'') + '→' + coalesce(n.nbr_label,'') +
       CASE WHEN n.nbr_name IS NULL OR n.nbr_name = '' THEN '' ELSE ':' + n.nbr_name END
     ) AS neighbors_s

RETURN
  coalesce(node.name, '') + ' [' + head(labels(node)) + ']' +
  // KPI details if node is a KPI
  CASE WHEN node:KPI AND kpi_status IS NOT NULL THEN
       ' — KPI Status: ' + kpi_status +
       ' (current ' + toString(cv) + ', target ' + toString(tgt) +
       ', threshold ' + toString(thr) + ', direction ' + coalesce(dir,'') + ')'
       ELSE ''
  END +
  CASE WHEN node:KPI AND (direct_risks_s <> '' OR obj_risks_s <> '' OR obj_objs_s <> '') THEN
       ' | Root causes: ' +
       CASE WHEN direct_risks_s <> '' THEN 'Direct[' + direct_risks_s + ']' ELSE '' END +
       CASE WHEN (direct_risks_s <> '' AND obj_risks_s <> '') THEN '; ' ELSE '' END +
       CASE WHEN obj_risks_s <> '' THEN 'Via Objectives[' + obj_risks_s +
            CASE WHEN obj_objs_s <> '' THEN ' @ ' + obj_objs_s ELSE '' END + ']' ELSE '' END
       ELSE ''
  END +
  // BusinessUnit health if available
  CASE WHEN node:BusinessUnit AND bu_health IS NOT NULL THEN
       ' — Health: ' + bu_health +
       ' (current ' + toString(bukpi.current_value) + ', target ' + toString(bukpi.target) +
       ', threshold ' + toString(bukpi.threshold) + ')'
       ELSE ''
  END +
  // For non-KPI nodes, summarize KPI performance counts
  CASE WHEN NOT node:KPI AND (size(under_kpis) > 0 OR size(ontrack_kpis) > 0) THEN
       ' | KPIs Off Track: ' + toString(size(under_kpis)) +
       '; On Track: ' + toString(size(ontrack_kpis))
       ELSE ''
  END +
  // Neighbors for extra context
  CASE WHEN neighbors_s <> '' THEN ' | Neighbors: ' + neighbors_s ELSE '' END
  AS text,
  head(labels(node)) AS node_type,
  score
ORDER BY score DESC
LIMIT 50
"""

# =========================
# RAG ENGINE
# =========================
retriever = VectorCypherRetriever(
    driver=driver,
    index_name=INDEX_NAME,
    embedder=embedder,
    retrieval_query=RETRIEVAL_QUERY
)

rag = GraphRAG(
    retriever=retriever,
    llm=llm
)

# =========================
# DIRECT (DETERMINISTIC) CYPHER FOR POPULAR QUESTION
# =========================
CY_HEALTH_BY_BU = """
MATCH (bu:BusinessUnit)<-[:MEASURES|:TRACKS]-(k:KPI)
WHERE k.name CONTAINS 'Health Score'
WITH bu, k,
     CASE
       WHEN k.current_value >= k.target THEN 'Healthy'
       WHEN k.current_value < k.threshold THEN 'Not Healthy'
       ELSE 'At Risk'
     END AS health
RETURN bu.name AS business_unit,
       k.current_value AS score,
       k.target AS target,
       k.threshold AS threshold,
       health
ORDER BY
  CASE health WHEN 'Healthy' THEN 0 WHEN 'At Risk' THEN 1 ELSE 2 END,
  bu.name
"""

def looks_like_bu_health_question(q: str) -> bool:
    q_low = q.lower()
    return (
        ("which" in q_low or "show" in q_low or "list" in q_low)
        and ("business unit" in q_low or "bus" in q_low or "bu" in q_low)
        and ("health" in q_low or "healthy" in q_low or "not healthy" in q_low)
    )

def answer_bu_health_direct():
    with driver.session() as session:
        rows = session.run(CY_HEALTH_BY_BU).data()

    healthy = [r for r in rows if r["health"] == "Healthy"]
    at_risk = [r for r in rows if r["health"] == "At Risk"]
    not_healthy = [r for r in rows if r["health"] == "Not Healthy"]

    def fmt(rows):
        return "\n".join(
            f"- {r['business_unit']} — {r['score']} (target {r['target']}, threshold {r['threshold']})"
            for r in rows
        ) or "- None"

    parts = []
    parts.append("### Healthy\n" + fmt(healthy))
    if at_risk:
        parts.append("\n### At Risk\n" + fmt(at_risk))
    parts.append("\n### Not Healthy\n" + fmt(not_healthy))

    return "\n".join(parts)

# =========================
# CHAT LOOP
# =========================
def start_chatbot():
    signal.signal(signal.SIGINT, signal_handler)

    # Ensure index exists
    with driver.session() as session:
        idx_names = [rec["name"] for rec in session.run("SHOW INDEXES")]
        if INDEX_NAME not in idx_names:
            print("❌ No embedding index found, creating one...")
            setup_vector_index()
        else:
            print(f"✅ Using existing index: {INDEX_NAME}")

    print("\n💬 Ready! Ask a business question (type 'exit' to quit):")
    while True:
        query = input("\n> ")
        if query.strip().lower() in ("exit", "quit"):
            break

        # Fast-path: deterministic Cypher for BU health
        if looks_like_bu_health_question(query):
            print("\n---\nAnswer:\n" + answer_bu_health_direct())
            continue

        # guided_query = f"{GRAPH_ANALYST_INSTRUCTION}\n\nQuestion: {query}"

        spinner = Spinner("🤔 Thinking")
        spinner.start()
        try:
            # Wider recall for portfolio-wide questions
            try:
                response = rag.search(query_text=query, retriever_config={"top_k": 100})
            except Exception:
                # Simple one-time retry for transient connection hiccups
                time.sleep(0.8)
                response = rag.search(query_text=query, retriever_config={"top_k": 100})

            spinner.stop()
            print("\n---\nAnswer:\n", response.answer)
        except Exception as e:
            spinner.stop()
            print("Error:", e)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_embeddings()

    tag_searchable_nodes()
    setup_vector_index()
    backfill_embeddings(batch_size=1000)
    start_chatbot()
    driver.close()
