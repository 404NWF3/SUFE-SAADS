GET_COMPONENT_BY_CODE = """
SELECT
    component_id, component_code, component_name, vendor_name, component_type, modality,
    purl, homepage_uri, lifecycle_status, created_at
FROM wp11.ai_component
WHERE component_code = %(component_code)s
"""

GET_COMPONENT_BY_NAME = """
SELECT
    component_id, component_code, component_name, vendor_name, component_type, modality,
    purl, homepage_uri, lifecycle_status, created_at
FROM wp11.ai_component
WHERE lower(component_name) = lower(%(component_name)s)
"""

CREATE_COMPONENT = """
INSERT INTO wp11.ai_component (
    component_code, component_name, vendor_name, component_type, modality, purl, homepage_uri, lifecycle_status
)
VALUES (
    %(component_code)s, %(component_name)s, %(vendor_name)s, %(component_type)s, %(modality)s,
    %(purl)s, %(homepage_uri)s, %(lifecycle_status)s
)
RETURNING
    component_id, component_code, component_name, vendor_name, component_type, modality,
    purl, homepage_uri, lifecycle_status, created_at
"""

INSERT_COMPONENT_ALIAS = """
INSERT INTO wp11.ai_component_alias (
    component_id, alias_name, alias_type, normalized_alias, is_preferred
)
VALUES (
    %(component_id)s, %(alias_name)s, %(alias_type)s, %(normalized_alias)s, %(is_preferred)s
)
RETURNING alias_id, component_id, alias_name, alias_type, normalized_alias, is_preferred
"""

LIST_COMPONENT_ALIASES = """
SELECT alias_id, component_id, alias_name, alias_type, normalized_alias, is_preferred
FROM wp11.ai_component_alias
WHERE component_id = %(component_id)s
ORDER BY is_preferred DESC, alias_id ASC
"""

GET_COMPONENT_BY_NORMALIZED_ALIAS = """
SELECT
    ac.component_id, ac.component_code, ac.component_name, ac.vendor_name, ac.component_type, ac.modality,
    ac.purl, ac.homepage_uri, ac.lifecycle_status, ac.created_at
FROM wp11.ai_component_alias a
JOIN wp11.ai_component ac ON ac.component_id = a.component_id
WHERE a.normalized_alias = %(normalized_alias)s
LIMIT 1
"""

SEARCH_COMPONENT_ALIAS = """
SELECT
    a.alias_id,
    a.component_id,
    a.alias_name,
    a.alias_type,
    a.normalized_alias,
    a.is_preferred,
    similarity(a.normalized_alias, %(normalized_alias)s) AS similarity
FROM wp11.ai_component_alias a
WHERE a.normalized_alias %% %(normalized_alias)s
ORDER BY similarity DESC, a.is_preferred DESC
LIMIT %(limit)s
"""

UPSERT_ATTACK_COMPONENT_IMPACT = """
INSERT INTO wp11.attack_component_impact (
    attack_id, component_id, version_constraint_raw, normalized_constraint, match_mode,
    impact_scope, confidence_score, evidence_uri
)
VALUES (
    %(attack_id)s, %(component_id)s, %(version_constraint_raw)s, %(normalized_constraint)s, %(match_mode)s,
    %(impact_scope)s, %(confidence_score)s, %(evidence_uri)s
)
ON CONFLICT (
    attack_id, component_id, COALESCE(normalized_constraint, ''), impact_scope
)
DO UPDATE SET
    match_mode = EXCLUDED.match_mode,
    confidence_score = EXCLUDED.confidence_score,
    evidence_uri = EXCLUDED.evidence_uri,
    version_constraint_raw = EXCLUDED.version_constraint_raw
RETURNING
    impact_id, attack_id, component_id, version_constraint_raw, normalized_constraint, match_mode,
    impact_scope, confidence_score, evidence_uri, created_at
"""

LIST_COMPONENT_IMPACTS_BY_ATTACK = """
SELECT
    impact_id, attack_id, component_id, version_constraint_raw, normalized_constraint, match_mode,
    impact_scope, confidence_score, evidence_uri, created_at
FROM wp11.attack_component_impact
WHERE attack_id = %(attack_id)s
ORDER BY confidence_score DESC, created_at DESC
"""

LIST_ATTACKS_BY_COMPONENT = """
SELECT
    impact_id, attack_id, component_id, version_constraint_raw, normalized_constraint, match_mode,
    impact_scope, confidence_score, evidence_uri, created_at
FROM wp11.attack_component_impact
WHERE component_id = %(component_id)s
ORDER BY confidence_score DESC, created_at DESC
"""

