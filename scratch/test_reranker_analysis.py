import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from ai.rag.retrieval.retrieve_bns import retrieve

def _extract_incident_facts(incident_text: str):
    text = incident_text.lower()

    has_clerk_servant = bool(re.search(r'\b(clerk|servant|employee|employer|master|working as|hired by|assistant|worker)\b', text))
    has_assault_force = bool(re.search(r'\b(assault|assaulted|force|criminal force|attacked|slapped|hit|beat|beaten|pushed|struck|punch|punched|punches|hurt|injury|injured|bleeding|wound|wounded|threatened with force)\b', text))
    has_preparation = bool(re.search(r'\b(preparation|prepared|armed|weapon|gun|pistol|knife|deadly weapon|in order to hurt|to restrain|with intent to hurt)\b', text))
    has_mint_coining = bool(re.search(r'\b(mint|coining|coin tool|coining tool|coining instrument|minting|stamping coin)\b', text))
    has_taking_without_consent = bool(re.search(r'\b(took|take|stole|steal|taken|stolen|without permission|without consent|dispossessed|movable property)\b', text))
    has_concealment_only = bool(re.search(r'\b(conceal|concealed|concealment|hide|hidden|released claim|fraudulent removal)\b', text)) and not has_taking_without_consent

    has_dwelling_transport = bool(re.search(r'\b(dwelling house|dwelling|residence|residential house|house|home|building|premises|place of worship|temple|church|mosque|vessel|ship|boat|train|bus|car|vehicle|transportation)\b', text))
    has_unauthorized_entry = bool(re.search(r'\b(entered|entry|entered into|trespass|trespassed|without permission|without consent|unlawful entry|refused to leave|remains unlawfully)\b', text))
    has_gift_recovery = bool(re.search(r'\b(taking gift|gift|reward|gratification|reward to recover|help to recover|recovering stolen property)\b', text))
    has_property_mark = bool(re.search(r'\b(property mark|trade mark|trademark|brand mark|counterfeiting mark)\b', text))
    has_public_way_navigation = bool(re.search(r'\b(public way|line of navigation|navigation|public road|public street|road|highway|traffic|driving|driven|driver|vehicle|car|motorcycle|scooter|bus|truck|accident|collision)\b', text))
    has_omission_to_inform = bool(re.search(r'\b(omission to give information|failed to inform|bound to inform|omission to report)\b', text))
    has_receiving_stolen = bool(re.search(r'\b(received stolen|retained stolen|buying stolen|bought stolen|possessing stolen property)\b', text)) and not has_taking_without_consent

    # Target & qualification specific incident facts
    has_woman = bool(re.search(r'\b(woman|women|female|girl|lady|wife|daughter|she|her|herself)\b', text))
    has_public_servant = bool(re.search(r'\b(public servant|government servant|policeman|police officer|officer|official|magistrate|judge)\b', text))
    has_confinement = bool(re.search(r'\b(confined|confine|wrongful confinement|locked in|detained|held captive|hostage)\b', text))
    has_dishonour = bool(re.search(r'\b(dishonour|humiliate|humiliation|blackmail)\b', text))
    has_grievous_weapon = bool(re.search(r'\b(grievous|fracture|deadly weapon|weapon|gun|pistol|knife|sword|acid)\b', text))
    has_abetment = bool(re.search(r'\b(instigated|abetted|conspired|helped to commit|accomplice)\b', text))
    has_provocation = bool(re.search(r'\b(provoked|provocation|taunted|insulted first)\b', text))
    has_official_high_person = bool(re.search(r'\b(president|governor|soldier|sailor|airman|superior officer)\b', text))

    return {
        "clerk_servant": has_clerk_servant,
        "assault_force": has_assault_force,
        "preparation": has_preparation,
        "mint_coining": has_mint_coining,
        "taking_without_consent": has_taking_without_consent,
        "concealment_only": has_concealment_only,
        "dwelling_transport": has_dwelling_transport,
        "unauthorized_entry": has_unauthorized_entry,
        "gift_recovery": has_gift_recovery,
        "property_mark": has_property_mark,
        "public_way_navigation": has_public_way_navigation,
        "omission_to_inform": has_omission_to_inform,
        "receiving_stolen": has_receiving_stolen,
        "woman": has_woman,
        "public_servant": has_public_servant,
        "confinement": has_confinement,
        "dishonour": has_dishonour,
        "grievous_weapon": has_grievous_weapon,
        "abetment": has_abetment,
        "provocation": has_provocation,
        "official_high_person": has_official_high_person,
    }

def _analyze_candidate_requirements(candidate):
    title = str(candidate.get("title", "")).lower()
    text = str(candidate.get("text", "")).lower()

    text_operative = text.split("illustrations")[0] if "illustrations" in text else text
    full_target_str = f"{title} {text_operative}"

    requires_clerk_servant = bool(re.search(r'\b(clerk or servant|theft by clerk|in the capacity of a clerk|in possession of master|master or employer)\b', full_target_str)) or ("clerk" in title or "servant" in title)
    requires_assault_force = bool(re.search(r'\b(assault or criminal force|uses assault|assault in attempt|criminal force in attempt|voluntarily causing hurt|causing hurt)\b', full_target_str)) or ("assault" in title or "criminal force" in title or "hurt" in title)
    requires_preparation = bool(re.search(r'\b(preparation made for causing|preparation for causing|having made preparation)\b', full_target_str)) or ("preparation made" in title or "preparation for" in title)
    requires_mint_coining = bool(re.search(r'\b(coining tool|coining instrument|out of any mint|takes out of any mint)\b', full_target_str)) or ("mint" in title or "coining" in title)
    requires_concealment = bool(re.search(r'\b(conceals or removes|concealment or removal|dishonestly releases any demand)\b', full_target_str)) or ("concealment" in title)

    requires_dwelling_transport = bool(re.search(r'\b(dwelling house|means of transportation|place of worship|building, tent or vessel|building|house)\b', full_target_str)) or ("dwelling house" in title or "means of transportation" in title or "place of worship" in title or "house" in title)
    requires_trespass_entry = bool(re.search(r'\b(criminal trespass|house-trespass|house trespass|enters into or upon property|unlawfully remains)\b', full_target_str)) or ("trespass" in title)
    requires_gift_recovery = bool(re.search(r'\b(taking gift|help to recover stolen property|gratification|taking gift to help)\b', full_target_str)) or ("taking gift" in title or "recover stolen property" in title)
    requires_property_mark = bool(re.search(r'\b(property mark|counterfeiting a property mark|tampering with property mark)\b', full_target_str)) or ("property mark" in title)
    requires_public_way_navigation = bool(re.search(r'\b(public way|line of navigation|navigation|rash driving|riding on a public way|driving any vehicle|vehicle|road)\b', full_target_str)) or ("public way" in title or "line of navigation" in title or "driving" in title or "riding" in title)
    requires_omission_to_inform = bool(re.search(r'\b(omission to give information|person bound to inform|intentional omission)\b', full_target_str)) or ("omission to give information" in title or "bound to inform" in title)
    requires_receiving_stolen = bool(re.search(r'\b(dishonestly receives or retains|receives any stolen property|retains any stolen property)\b', full_target_str)) or (title.strip().startswith("stolen property"))

    requires_woman = bool(re.search(r'\b(woman|female|girl|disrobe|modesty|outrage her modesty)\b', full_target_str)) or ("woman" in title or "female" in title or "disrobe" in title)
    requires_public_servant = bool(re.search(r'\b(public servant|government servant|public officer|deter public servant)\b', full_target_str)) or ("public servant" in title)
    requires_confinement = bool(re.search(r'\b(wrongful confinement|wrongfully to confine|confine a person|attempt wrongfully to confine)\b', full_target_str)) or ("confine" in title or "confinement" in title)
    requires_dishonour = bool(re.search(r'\b(intent to dishonour|dishonour person)\b', full_target_str)) or ("dishonour" in title)
    requires_grievous_dangerous = bool(re.search(r'\b(grievous hurt|dangerous weapons|dangerous means|deadly weapon)\b', full_target_str)) or ("grievous" in title or "dangerous" in title)
    requires_abetment = bool(re.search(r'\b(abetment of|abetted|abetment)\b', full_target_str)) or ("abetment" in title)
    requires_provocation = bool(re.search(r'\b(grave provocation|grave and sudden provocation)\b', full_target_str)) or ("grave provocation" in title)
    requires_official_high_person = bool(re.search(r'\b(president|governor|soldier|sailor|airman|superior officer)\b', full_target_str)) or ("president" in title or "governor" in title or "soldier" in title)

    is_general_theft = bool(re.search(r'\b(intending to take dishonestly any movable property|out of the possession of any person without that person\'s consent|moves that property)\b', text)) or title.strip() in ["theft.", "theft"]
    is_general_hurt = bool(re.search(r'\b(voluntarily to cause hurt|does any act with the intention of thereby causing hurt)\b', text)) or title.strip() in ["voluntarily causing hurt.", "voluntarily causing hurt", "causing hurt.", "causing hurt"]
    is_snatching = "snatching" in title.lower() or "snatching" in text_operative

    return {
        "requires_clerk_servant": requires_clerk_servant,
        "requires_assault_force": requires_assault_force,
        "requires_preparation": requires_preparation,
        "requires_mint_coining": requires_mint_coining,
        "requires_concealment": requires_concealment,
        "requires_dwelling_transport": requires_dwelling_transport,
        "requires_trespass_entry": requires_trespass_entry,
        "requires_gift_recovery": requires_gift_recovery,
        "requires_property_mark": requires_property_mark,
        "requires_public_way_navigation": requires_public_way_navigation,
        "requires_omission_to_inform": requires_omission_to_inform,
        "requires_receiving_stolen": requires_receiving_stolen,
        "requires_woman": requires_woman,
        "requires_public_servant": requires_public_servant,
        "requires_confinement": requires_confinement,
        "requires_dishonour": requires_dishonour,
        "requires_grievous_dangerous": requires_grievous_dangerous,
        "requires_abetment": requires_abetment,
        "requires_provocation": requires_provocation,
        "requires_official_high_person": requires_official_high_person,
        "is_general_theft": is_general_theft,
        "is_general_hurt": is_general_hurt,
        "is_snatching": is_snatching,
    }

def rerank_candidates(incident_input, candidates):
    incident_facts = _extract_incident_facts(incident_input)
    reranked = []

    for idx, cand in enumerate(candidates):
        orig_distance = float(cand.get("distance", 1.0))
        similarity_score = max(0.0, 1.0 - (orig_distance / 2.0))
        score = similarity_score

        cand_reqs = _analyze_candidate_requirements(cand)

        # General Theft / Snatching Core Alignment
        if cand_reqs["is_general_theft"] or cand_reqs["is_snatching"]:
            if incident_facts["taking_without_consent"]:
                score += 0.45

        # General Hurt Core Alignment
        if cand_reqs["is_general_hurt"]:
            if incident_facts["assault_force"]:
                score += 0.45

        # Clerk / Servant requirement
        if cand_reqs["requires_clerk_servant"]:
            if incident_facts["clerk_servant"]:
                score += 0.45
            else:
                score -= 0.30

        # Assault / Criminal Force requirement
        if cand_reqs["requires_assault_force"]:
            if incident_facts["assault_force"]:
                score += 0.45
            else:
                score -= 0.25

        # Specialized target/element checks
        if cand_reqs["requires_woman"]:
            if incident_facts["woman"]:
                score += 0.35
            else:
                score -= 0.35

        if cand_reqs["requires_public_servant"]:
            if incident_facts["public_servant"]:
                score += 0.35
            else:
                score -= 0.35

        if cand_reqs["requires_confinement"]:
            if incident_facts["confinement"]:
                score += 0.35
            else:
                score -= 0.35

        if cand_reqs["requires_dishonour"]:
            if incident_facts["dishonour"]:
                score += 0.30
            else:
                score -= 0.25

        if cand_reqs["requires_grievous_dangerous"]:
            if incident_facts["grievous_weapon"]:
                score += 0.35
            else:
                score -= 0.25

        if cand_reqs["requires_abetment"]:
            if incident_facts["abetment"]:
                score += 0.35
            else:
                score -= 0.35

        if cand_reqs["requires_provocation"]:
            if incident_facts["provocation"]:
                score += 0.35
            else:
                score -= 0.35

        if cand_reqs["requires_official_high_person"]:
            if incident_facts["official_high_person"]:
                score += 0.40
            else:
                score -= 0.40

        cand_copy = dict(cand)
        cand_copy["rerank_score"] = round(score, 4)
        reranked.append(cand_copy)

    reranked.sort(key=lambda x: x.get("rerank_score", -999.0), reverse=True)
    return reranked

TEST_INCIDENT = (
    "Yesterday at around 7:30 PM, I was near the local market when an unknown man "
    "suddenly punched me and stole my mobile phone. I don't know the person who did it."
)

sample_queries = [
    TEST_INCIDENT,
    "stolen mobile phone punched by unknown person",
    "voluntarily causing hurt theft mobile phone assault",
    "theft of movable property physical punch hurt"
]

candidate_map = {}
for q in sample_queries:
    res = retrieve(query=q, top_k=20)
    for item in res:
        doc_id = item.get("id")
        if doc_id not in candidate_map or item.get("distance", 1.0) < candidate_map[doc_id].get("distance", 1.0):
            candidate_map[doc_id] = item

cands = list(candidate_map.values())
reranked = rerank_candidates(TEST_INCIDENT, cands)

print("\nTOP 10 RERANKED RESULTS FOR ACTUAL RETRIEVAL:")
for idx, r in enumerate(reranked[:10]):
    sec = r.get("section") or r.get("metadata", {}).get("section")
    title = r.get("title") or r.get("metadata", {}).get("title")
    print(f"  {idx+1}. BNS Section {sec}: {title} (score: {r['rerank_score']:.4f}, dist: {r.get('distance'):.4f})")
