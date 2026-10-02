import math
import re
from hashlib import sha256

from app.ai.base import BaseAIProvider, TicketAnalysis
from app.core.config import settings

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "hardware": [
        "monitor", "keyboard", "mouse", "laptop", "computer", "desktop", "printer", "battery",
        "charger", "screen", "display", "usb", "dock", "cpu", "ram", "ssd", "hard drive", "hdmi",
        "speaker", "kvm", "cable", "power", "fan", "webcam", "camera", "headset", "machine",
    ],
    "software": [
        "software", "install", "update", "upgrade", "error", "crash", "bug", "application",
        "app", "excel", "word", "outlook", "powerpoint", "teams", "slack", "windows", "macos",
        "linux", "license", "version", "glitch", "freeze", "load", "browser", "chrome",
        "firefox", "plugin", "exe", "driver", "configure", "configuration", "settings file",
    ],
    "network": [
        "wifi", "internet", "network", "router", "vpn", "dns", "connection", "connectivity",
        "server down", "cloud", "bandwidth", "firewall", "vlan", "ethernet", "downtime",
        "latency", "offline", "ping", "ip address", "proxy", "port", "remote access", "slow internet",
    ],
    "access": [
        "login", "password", "account", "permission", "access", "authorization", "auth",
        "user role", "lockout", "unauthorized", "reset", "unlock", "mfa", "2fa", "otp",
        "credentials", "sso", "sign in", "sign-in", "can't log", "cannot log", "restricted",
    ],
}

PRIORITY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "down", "outage", "urgent", "emergency", "critical", "all users", "production",
        "data loss", "security breach", "hacked", "ransomware", "cannot work", "completely",
        "dead", "bricked", "out of service", "site down",
    ],
    "high": [
        "unable", "can't work", "cannnot work", "blocked", "important", "asap", "soon",
        "deadline", "deploy", "release", "stopped working", "not working", "won't start",
        "failing", "high impact",
    ],
    "medium": [
        "slow", "error", "issue", "intermittent", "glitchy", "sometimes", "occasionally",
        "crash", "frozen", "delayed", "lagging",
    ],
    "low": [
        "minor", "question", "how to", "request", "tip", "when you have time", "cosmetic",
        "typo", "enhancement", "suggestion", "nice to have", "curious",
    ],
}

CATEGORY_FIX: dict[str, str] = {
    "hardware": "Try rebooting the device and reseating cables/peripherals. If the issue persists, verify "
    "warranty and schedule a hardware swap.",
    "software": "Restart the application, check for updates, and reinstall as a last resort. Clear the "
    "application cache first.",
    "network": "Restart the network adapter and router, then verify VPN/DNS settings. Check connectivity with "
    "a ping test.",
    "access": "Verify the user account is active and permissions are correct. Reset the password / MFA via "
    "the identity portal.",
    "other": "Review the ticket description, reproduce the issue, and escalate to the relevant team if needed.",
}


class HeuristicProvider(BaseAIProvider):
    """Deterministic, keyword/rule based analysis. Runs with no external API."""

    kind = "heuristic"

    def classify(self, title: str, description: str) -> TicketAnalysis:
        text = f"{title} {description}".lower()
        text = re.sub(r"\s+", " ", text)

        scores: dict[str, int] = {}
        for cat, kws in CATEGORY_KEYWORDS.items():
            scores[cat] = sum(kw in text for kw in kws)
        category = max(scores, key=scores.get) if any(scores.values()) else "other"
        if sum(scores.values()) == 0:
            category = "other"

        priority_scores = {
            name: sum(kw in text for kw in kws)
            for name, kws in PRIORITY_KEYWORDS.items()
        }
        weighted = {
            name: count * {"critical": 3, "high": 2, "medium": 1.5, "low": 1}[name]
            for name, count in priority_scores.items()
        }
        total = sum(weighted.values())
        priority = "medium" if total == 0 else max(weighted, key=weighted.get)

        summary = self._summary(title, description)
        fix = self._suggested_fix(category, text)

        best_matches = max(1, max(priority_scores.values(), default=0))
        confidence = min(0.99, 0.45 + (total / 5) + (best_matches / 8))

        return TicketAnalysis(
            category=category,
            priority=priority,
            summary=summary,
            suggested_fix=fix,
            confidence=round(confidence, 3),
        )

    def embed(self, text: str) -> list[float]:
        dim = settings.embedding_dim
        vec = [0.0] * dim
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        grams: list[str] = []
        if len(tokens) >= 3:
            grams = [" ".join(tokens[i : i + 3]) for i in range(len(tokens) - 2)]
        grams.extend(tokens)
        for gram in grams:
            digest = sha256(gram.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:8], byteorder="big") % dim
            sign = 1.0 if digest[0] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    @staticmethod
    def _summary(title: str, description: str) -> str:
        body = re.sub(r"\s+", " ", description.strip())
        if not body:
            return title
        return (title + " — " + body)[:200]

    @staticmethod
    def _suggested_fix(category: str, text: str) -> str:
        base = CATEGORY_FIX.get(category, CATEGORY_FIX["other"])
        if category != "other":
            return f"[{category}]. {base}"
        return base


def vector_to_string(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"
