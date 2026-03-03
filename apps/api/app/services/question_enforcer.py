def enforce_single_question(text: str, next_question: str) -> str:
    """
    Enforces that the LLM only asks EXACTLY ONE question at the end of its response.
    Strips trailing questions and appends the funnel-governed question.
    """
    if not next_question:
        return text.strip()
        
    lines = text.strip().split('\n')
    
    # Strip trailing lines that look like questions to prevent double-questioning
    while lines and ('?' in lines[-1] or lines[-1].strip().lower().startswith(('what', 'how', 'when', 'where', 'are', 'is', 'would', 'could', 'please'))):
        lines.pop()
        
    cleaned_text = '\n'.join(lines).strip()
    
    # Append the exact mandated question
    if cleaned_text:
        return f"{cleaned_text}\n\n{next_question}"
    return next_question
