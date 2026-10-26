import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.storage import Storage

def inspect():
    storage = Storage()
    docs = storage.get_documents()
    facts = storage.get_facts()
    relationships = storage.get_relationships()

    by_type = {
        "CORROBORATES": [],
        "CONTRADICTS": [],
        "CONTEXTUALIZES": [],
        "UNCERTAIN": []
    }

    for rel in relationships:
        type_str = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
        if type_str in by_type:
            by_type[type_str].append(rel)

    print("=== FINAL DATABASE STATE ===")
    print(f"Documents: {len(docs)}")
    print(f"Facts: {len(facts)}")
    print(f"Relationships: {len(relationships)}")
    print()
    print("=== RELATIONSHIP BREAKDOWN ===")
    print(f"CORROBORATES: {len(by_type['CORROBORATES'])}")
    print(f"CONTRADICTS: {len(by_type['CONTRADICTS'])}")
    print(f"CONTEXTUALIZES: {len(by_type['CONTEXTUALIZES'])}")
    print(f"UNCERTAIN: {len(by_type['UNCERTAIN'])}")
    print()

    doc_dict = {d.id: d.filename for d in docs}
    fact_dict = {f.id: f for f in facts}

    categories = ["CORROBORATES", "CONTRADICTS", "CONTEXTUALIZES", "UNCERTAIN"]

    for cat in categories:
        print(f"=== {cat} EXAMPLES ===")
        rels = by_type[cat][:5]
        if not rels:
            print("No examples found.\n")
            continue

        for i, rel in enumerate(rels, 1):
            fa = fact_dict.get(rel.fact_a_id)
            fb = fact_dict.get(rel.fact_b_id)
            print(f"Example {i}:")
            if fa and fb:
                print(f"  Doc A: {doc_dict.get(fa.evidence.document_id, fa.evidence.document_name)}")
                print(f"  Predicate A: {fa.predicate} | Value A: {fa.value.raw} | Context A: Time={fa.context.time}, Scope={fa.context.scope}, Geo={fa.context.geography}")
                print(f"  Evidence A: \"{fa.evidence.text}\"")
                print(f"  Doc B: {doc_dict.get(fb.evidence.document_id, fb.evidence.document_name)}")
                print(f"  Predicate B: {fb.predicate} | Value B: {fb.value.raw} | Context B: Time={fb.context.time}, Scope={fb.context.scope}, Geo={fb.context.geography}")
                print(f"  Evidence B: \"{fb.evidence.text}\"")
            else:
                print(f"  Fact A ID: {rel.fact_a_id}, Fact B ID: {rel.fact_b_id}")
            print(f"  Reason: {rel.reason}")
            print()

if __name__ == "__main__":
    inspect()
