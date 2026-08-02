# =====================================================================
# cypher_templates.py — SAFE CYPHER GENERATION
# =====================================================================

ALLOWED_LABELS = {"Movie", "Director", "Actor", "Genre", "Theme", "Award"}

ALLOWED_RELATIONSHIPS = {"DIRECTED", "ACTED_IN", "BELONGS_TO", "EXPLORES", "WON"}

ALLOWED_PROPERTIES = {
    "Movie": ["title", "year"],
    "Director": ["name"],
    "Actor": ["name"],
    "Genre": ["name"],
    "Theme": ["name"],
    "Award": ["name", "category"],
}

ALLOWED_OPERATORS = {"=", "<>", ">", "<", ">=", "<=", "CONTAINS", "STARTS WITH"}

LABEL_VAR_MAP = {
    "Movie": "m",
    "Director": "d",
    "Actor": "a",
    "Genre": "g",
    "Theme": "t",
    "Award": "aw",
}

def validate_step(step: dict):
    """Validate ONE step from the plan against strict whitelists."""
    step_type = step.get("type")

    if step_type == "traversal":
        from_lbl = step.get("from")
        to_lbl = step.get("to")
        rel = step.get("rel")
        if from_lbl not in ALLOWED_LABELS:
            raise ValueError(f"Invalid label: {from_lbl}")
        if to_lbl not in ALLOWED_LABELS:
            raise ValueError(f"Invalid label: {to_lbl}")
        if rel not in ALLOWED_RELATIONSHIPS:
            raise ValueError(f"Invalid relationship: {rel}")

    elif step_type == "filter":
        field = step.get("field", "")
        if "." not in field:
            raise ValueError(f"Invalid filter field format: {field}")
        label, prop = field.split(".", 1)
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid label: {label}")
        if prop not in ALLOWED_PROPERTIES.get(label, []):
            raise ValueError(f"Invalid property: {field}")
        op = step.get("op")
        if op not in ALLOWED_OPERATORS:
            raise ValueError(f"Invalid operator: {op}")

    elif step_type == "projection":
        fields = step.get("fields", [])
        for field in fields:
            if "." not in field:
                raise ValueError(f"Invalid projection field format: {field}")
            lbl, prp = field.split(".", 1)
            if lbl not in ALLOWED_LABELS:
                raise ValueError(f"Invalid label: {lbl}")
            if prp not in ALLOWED_PROPERTIES.get(lbl, []):
                raise ValueError(f"Invalid property: {field}")

    elif step_type == "aggregation":
        func = step.get("function")
        valid_aggs = ["count", "collect", "sum", "avg", "min", "max"]
        if func not in valid_aggs:
            raise ValueError(f"Invalid aggregation function: {func}")

    elif step_type == "sort":
        field = step.get("field", "")
        if "." in field:
            lbl, prp = field.split(".", 1)
            if lbl not in ALLOWED_LABELS:
                raise ValueError(f"Invalid label: {lbl}")
        direction = str(step.get("direction", "")).upper()
        if direction not in ["ASC", "DESC"]:
            raise ValueError(f"Invalid sort direction: {direction}")

    elif step_type == "limit":
        val = step.get("value")
        if not isinstance(val, int) or val < 1 or val > 100:
            raise ValueError(f"Invalid limit: {val}")

    else:
        raise ValueError(f"Unknown step type: {step_type}")

def build_cypher(plan: dict) -> tuple[str, dict]:
    """
    Build safe Cypher from a validated plan.
    Input:  {'steps': [{ 'type': 'traversal', 'from': 'Director', ... }, ...]}
    Output: ('MATCH (d:Director)...', {'p0': 'James Cameron'})
    """
    steps = plan.get("steps", [])
    for step in steps:
        validate_step(step)

    match_clauses = []
    where_clauses = []
    return_clause = ""
    order_clause = ""
    limit_clause = ""
    params = {}
    param_counter = 0

    for step in steps:
        step_type = step.get("type")

        if step_type == "traversal":
            from_var = LABEL_VAR_MAP[step["from"]]
            to_var = LABEL_VAR_MAP[step["to"]]
            match_clauses.append(
                f"MATCH ({from_var}:{step['from']})-[:{step['rel']}]->({to_var}:{step['to']})"
            )

        elif step_type == "filter":
            label, prop = step["field"].split(".", 1)
            var_name = LABEL_VAR_MAP[label]
            param_name = f"p{param_counter}"
            param_counter += 1
            params[param_name] = step["value"]
            where_clauses.append(f"{var_name}.{prop} {step['op']} ${param_name}")

        elif step_type == "projection":
            fields = []
            for f in step.get("fields", []):
                lbl, prp = f.split(".", 1)
                fields.append(f"{LABEL_VAR_MAP[lbl]}.{prp}")
            distinct = "DISTINCT " if step.get("distinct") else ""
            return_clause = f"RETURN {distinct}{', '.join(fields)}"

        elif step_type == "aggregation":
            alias = step.get("alias") or f"{step['function']}_result"
            group_by = step.get("groupBy")
            field = step.get("field", "")

            if field and "." in field:
                agg_label = field.split(".", 1)[0]
                agg_target = LABEL_VAR_MAP.get(agg_label, "*")
            else:
                agg_target = "*"

            if group_by and "." in group_by:
                grp_label, grp_prop = group_by.split(".", 1)
                grp_var = LABEL_VAR_MAP[grp_label]
                return_clause = f"RETURN {grp_var}.{grp_prop}, {step['function']}({agg_target}) AS {alias}"
            else:
                return_clause = f"RETURN {step['function']}({agg_target}) AS {alias}"

        elif step_type == "sort":
            field = step["field"]
            direction = step["direction"].upper()
            if "." in field:
                lbl, prp = field.split(".", 1)
                s_var = LABEL_VAR_MAP[lbl]
                if f" AS {prp}" in return_clause:
                    order_clause = f"ORDER BY {prp} {direction}"
                else:
                    order_clause = f"ORDER BY {s_var}.{prp} {direction}"
            else:
                order_clause = f"ORDER BY {field} {direction}"

        elif step_type == "limit":
            limit_clause = f"LIMIT {step['value']}"

    cypher_parts = match_clauses + (
        [f"WHERE {' AND '.join(where_clauses)}"] if where_clauses else []
    ) + [return_clause, order_clause, limit_clause]

    cypher = "\n".join([p for p in cypher_parts if p.strip()])
    return cypher, params
