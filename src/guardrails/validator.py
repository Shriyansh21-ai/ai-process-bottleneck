def validate_output(text):
    forbidden = ["guess", "maybe", "unknown"]

    for word in forbidden:
        if word in text.lower():
            raise ValueError("Unreliable language detected")

    return text
