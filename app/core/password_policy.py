from __future__ import annotations
import re

COMMON_PASSWORDS = {
    "123456", "12345678", "123456789", "1234567890",
    "password", "password1", "password123", "qwerty", "qwerty123",
    "admin", "admin123", "letmein", "welcome", "welcome1",
    "rahasia", "rahasia123", "indonesia", "123456a", "abc123",
    "111111", "000000", "iloveyou", "monkey", "dragon",
}


def password_strength(password: str) -> dict:
    score = 0
    length = len(password)

    if length >= 8:
        score += 1
    if length >= 12:
        score += 1
    if any(char.islower() for char in password) and any(char.isupper() for char in password):
        score += 1
    if any(char.isdigit() for char in password):
        score += 1
    if any(not char.isalnum() for char in password):
        score += 1

    normalized = password.strip().lower()
    normalized_root = re.sub(r"[\d!@#$%^&*]+$", "", normalized)
    is_common = (
        normalized in COMMON_PASSWORDS
        or normalized_root in {"password", "admin", "qwerty", "welcome", "rahasia", "letmein"}
    )
    if is_common or len(set(normalized)) == 1:
        score = 0

    if score <= 1:
        level = "weak"
        label = "Lemah"
    elif score == 2:
        level = "fair"
        label = "Cukup"
    elif score in (3, 4):
        level = "good"
        label = "Baik"
    else:
        level = "strong"
        label = "Kuat"

    suggestions = []
    if length < 8:
        suggestions.append("Gunakan minimal 8 karakter.")
    if not any(char.isupper() for char in password) or not any(char.islower() for char in password):
        suggestions.append("Gabungkan huruf besar dan huruf kecil.")
    if not any(char.isdigit() for char in password):
        suggestions.append("Tambahkan angka.")
    if not any(not char.isalnum() for char in password):
        suggestions.append("Tambahkan simbol.")
    if is_common:
        suggestions.append("Password ini umum digunakan dan mudah ditebak.")
    if len(set(normalized)) < 4 and len(normalized) >= 8:
        suggestions.append("Hindari karakter yang berulang.")

    return {
        "score": score,
        "level": level,
        "label": label,
        "is_common": is_common,
        "suggestions": suggestions,
    }


def validate_password(password: str) -> None:
    result = password_strength(password)
    if len(password) < 8:
        raise ValueError("Password minimal 8 karakter")
    if result["is_common"]:
        raise ValueError("Password terlalu umum. Gunakan password yang lebih unik.")
