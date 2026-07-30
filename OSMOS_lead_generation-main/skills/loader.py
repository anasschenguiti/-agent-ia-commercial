import os

def load_skills() -> str:
    """
    Reads all markdown files inside skills/ and concatenates them
    into the final system prompt.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = [
        "system.md",
        "linkedin.md",
        "navigation.md",
        "interaction.md",
        "verification.md",
        "examples.md"
    ]
    
    content = []
    for filename in files:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content.append(f.read().strip())
    
    return "\n\n".join(content)
