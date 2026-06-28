import argparse
import json
import os
import struct
import zipfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "teams-manifest" / "dist"
COLOR_ICON = "color.png"
OUTLINE_ICON = "outline.png"


def png_bytes(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    red, green, blue, alpha = rgba
    row = bytes([red, green, blue, alpha]) * width
    raw = b"".join(b"\x00" + row for _ in range(height))

    def chunk(name: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(
        b"IDAT", zlib.compress(raw)
    ) + chunk(b"IEND", b"")


def normalized_host(host: str) -> str:
    value = host.strip().replace("https://", "").replace("http://", "")
    return value.split("/")[0]


def build_manifest(args: argparse.Namespace) -> dict:
    function_host = normalized_host(args.function_host)
    package_name = args.package_name or "com.example.dpsbot.pilot"
    return {
        "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
        "manifestVersion": "1.16",
        "version": args.version,
        "id": args.app_id,
        "packageName": package_name,
        "developer": {
            "name": args.developer_name,
            "websiteUrl": args.website_url,
            "privacyUrl": args.privacy_url,
            "termsOfUseUrl": args.terms_url,
        },
        "name": {"short": args.short_name, "full": args.full_name},
        "description": {
            "short": "Pilot bot that returns one Adaptive Card when mentioned.",
            "full": (
                "A limited DPSBot pilot used to verify Microsoft Teams, Azure Bot "
                "Service, and Azure Functions connectivity before adding Graph, "
                "Jira, storage, or Databricks integrations."
            ),
        },
        "icons": {"outline": OUTLINE_ICON, "color": COLOR_ICON},
        "accentColor": "#2563EB",
        "bots": [
            {
                "botId": args.app_id,
                "scopes": ["personal", "team"],
                "isNotificationOnly": False,
                "supportsFiles": False,
                "commandLists": [
                    {
                        "scopes": ["personal", "team"],
                        "commands": [
                            {
                                "title": "test",
                                "description": "Return the pilot Adaptive Card.",
                            }
                        ],
                    }
                ],
            }
        ],
        "permissions": ["identity"],
        "validDomains": [function_host],
    }


def write_package(manifest: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifest.json"
    color_path = OUTPUT_DIR / COLOR_ICON
    outline_path = OUTPUT_DIR / OUTLINE_ICON
    package_path = OUTPUT_DIR / "dpsbot-pilot-teams-app.zip"

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    color_path.write_bytes(png_bytes(192, 192, (37, 99, 235, 255)))
    outline_path.write_bytes(png_bytes(32, 32, (255, 255, 255, 255)))

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.write(manifest_path, "manifest.json")
        package.write(color_path, COLOR_ICON)
        package.write(outline_path, OUTLINE_ICON)

    return package_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the DPSBot pilot Teams app package.")
    parser.add_argument("--app-id", required=True, help="Entra application client ID.")
    parser.add_argument(
        "--function-host",
        required=True,
        help="Function host name, for example func-name.azurewebsites.net.",
    )
    parser.add_argument("--short-name", default="DPSBotPilot")
    parser.add_argument("--full-name", default="DPSBot Pilot - Mention Card Test")
    parser.add_argument("--version", default="0.0.1")
    parser.add_argument("--package-name", default=None)
    parser.add_argument("--developer-name", default="Your Organization")
    parser.add_argument("--website-url", default="https://example.com")
    parser.add_argument("--privacy-url", default="https://example.com/privacy")
    parser.add_argument("--terms-url", default="https://example.com/terms")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(args)
    package_path = write_package(manifest)
    relative_path = os.path.relpath(package_path, ROOT)
    print(f"Created Teams app package: {relative_path}")


if __name__ == "__main__":
    main()
