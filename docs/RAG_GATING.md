# RAG Retrieval Gating — PulseX-WDD

## Why Gating Matters

Without hard metadata filtering, a hybrid RAG system could return results for the wrong project. Example failure mode without gating:
- User asks: *"What are the amenities in Murano?"*
- System retrieves: Murano **and** Neo (both have "swimming pools" in their embeddings)
- Answer incorrectly mentions Neo amenities as if they belong to Murano

The gating system prevents this class of errors.

## Gating Rules (Priority Order)

### 1. Project Hard Gate (STRICTEST — never relaxed if user explicitly picked a project)
```
IF project_hint exists:
  KEEP only candidates where:
    entity_id == project_hint
    OR display_name casefold contains project_hint casefold
    OR is_alias_of == project_hint
    OR parent_project == project_hint
```

**Sources of project_hint:**
- `page_context.project_slug` (widget embed attribute `data-project`)
- Project name extracted from user message via `extract_project_hint()`

### 2. Region Gate
```
IF region_hint exists:
  KEEP only candidates where entity.region contains region_hint (case-insensitive substring match)
```

**Sources of region_hint:** Extracted from message keywords:
- "New Cairo" / "التجمع" → East Cairo
- "Ain Sokhna" / "السخنة" → Ain El Sokhna
- "North Coast" / "الساحل" → North Coast
- "Maadi" / "ماضي" → Cairo
- etc.

### 3. Unit Type Gate (softened)
```
IF unit_type_hint exists:
  KEEP candidates where unit_types list contains unit_type_hint
  IF zero candidates remain:
    RELAX — keep all candidates (log warning)
```

### 4. Budget Band (ranking only, no hard removal)
Used to rank results, not to eliminate. Budget filtering is only applied as hard gate if user says "under X million".

## Fallback Relaxation Order

If gating removes all candidates:
1. Relax `unit_type` filter first
2. Then relax `budget_band` filter  
3. **Never relax `project` filter** if user message explicitly names a project

## Score Blending

```
blended = 0.55 × normalize(keyword_score) + 0.45 × normalize(vector_score)
```

Weights configurable via `.env` (`keyword_weight`, `vector_weight`).

## Evidence Pack

From top-K gated results, return 2–5 snippets:
- `display_name` (project name)
- `snippet` (first 200 chars of `index_text`)
- `source_url` (verified WDD page URL)
- `confidence` (KB `confidence_score`)

If `answerability_confidence < 0.4`: trigger callback offer instead of attempting to answer.

## Example Scenarios

| User Input | Project Hint | Region Hint | Unit Hint | Result |
|---|---|---|---|---|
| "Tell me about Murano villas" | murano | — | villa | Only Murano family entities with villa unit type |
| "Apartments in New Cairo" | — | East Cairo | apartment | Neo, Neo Lakes, Promenade (East Cairo apartments only) |
| "What pools does ClubTown have?" | clubtown | — | — | ClubTown + Breeze + Horizon + Edge (all phases) |
| "Something in Ain Sokhna" | — | Ain El Sokhna | — | Murano, Waterside, Floating Islands, Ojo, Blumar variants |
