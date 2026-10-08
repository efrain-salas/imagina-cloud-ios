#!/usr/bin/env python3
"""Turns Nextcloud for iOS into Imagina Cloud. See IMAGINA.md.

Every file of Nextcloud that Imagina changes is rebuilt here from the Nextcloud release named in
imagina/imagina.properties (NEXTCLOUD_IOS_TAG), so running it again always gives the same result, and
after updating Nextcloud it is enough to run it with the new tag. Each change looks for an exact piece
of Nextcloud's code and stops with an error when it is not there (Nextcloud changed it: review the change).

Usage: python3 -I imagina/apply-branding.py   (from anywhere; it works on the repository it lives in)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGINA = ROOT / "imagina"


def read_parameters() -> dict:
    parameters = {}
    for name in ("imagina.properties", "imagina.local.properties"):
        path = IMAGINA / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                parameters[key.strip()] = value.strip()
    return parameters


P = read_parameters()
TAG = P["NEXTCLOUD_IOS_TAG"]
APP_ID = P["IMAGINA_APPLICATION_ID"]
APP_NAME = P["IMAGINA_APP_NAME"]
SCHEME = P["IMAGINA_URL_SCHEME"]
TEAM = P["IMAGINA_DEVELOPMENT_TEAM"]
GROUP = f"group.{APP_ID}"


class BrandingError(Exception):
    pass


def upstream(path: str) -> bytes:
    """The file as Nextcloud ships it in the release TAG."""
    try:
        return subprocess.run(["git", "-C", str(ROOT), "show", f"{TAG}:{path}"], check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as error:
        raise BrandingError(f"{path} is not in Nextcloud {TAG}: {error.stderr.decode().strip()}")


def replace(text: str, old: str, new: str, path: str, count: int | None = 1) -> str:
    found = text.count(old)
    if found == 0 or (count is not None and found != count):
        expected = "at least once" if count is None else f"{count} time(s)"
        raise BrandingError(f"{path}: expected {old!r} {expected}, found {found}")
    return text.replace(old, new)


def set_line(text: str, pattern: str, value: str, path: str) -> str:
    """Replaces the value of a single declaration line (`var name: Type = …`) keeping its indentation."""
    regex = re.compile(rf"^(\s*{pattern} = ).*$", re.MULTILINE)
    if len(regex.findall(text)) != 1:
        raise BrandingError(f"{path}: expected one line matching {pattern!r}")
    return regex.sub(lambda match: match.group(1) + value, text)


def swift_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------------------------------
# Identifiers, signing and the Imagina sources (Xcode project)

def brand_project() -> None:
    path = "Nextcloud.xcodeproj/project.pbxproj"
    text = upstream(path).decode()

    text = replace(text, '"it.twsweb.$(PRODUCT_NAME:rfc1034identifier)"', APP_ID, path, count=2)
    text = replace(text, "it.twsweb.Nextcloud.", f"{APP_ID}.", path, count=None)
    text = replace(text, "NKUJUXUJ3B", TEAM, path, count=None)

    # The team for every target, at project level (Xcode's automatic signing needs one).
    for configuration in ("F7F67BC91A24D27800EE80DA /* Debug */", "F7F67BCA1A24D27800EE80DA /* Release */"):
        anchor = f"\t\t{configuration} = {{\n\t\t\tisa = XCBuildConfiguration;\n\t\t\tbuildSettings = {{\n"
        text = replace(text, anchor, anchor + f"\t\t\t\tDEVELOPMENT_TEAM = {TEAM};\n", path)

    # imagina/Sources as a folder Xcode keeps in sync, compiled into the app target only.
    group_id = "1A1B25C10D0000000000C001"
    group = f"{group_id} /* Imagina */"
    text = replace(
        text,
        "/* End PBXFileSystemSynchronizedRootGroup section */",
        f'\t\t{group} = {{isa = PBXFileSystemSynchronizedRootGroup; explicitFileTypes = {{}}; explicitFolders = (); name = Imagina; path = imagina/Sources; sourceTree = "<group>"; }};\n'
        "/* End PBXFileSystemSynchronizedRootGroup section */",
        path,
    )
    main_group_child = "\t\t\t\tF7F67BAA1A24D27800EE80DA /* iOSClient */,\n"
    text = replace(text, main_group_child, main_group_child + f"\t\t\t\t{group},\n", path)
    text = replace(
        text,
        "\t\t\t);\n\t\t\tname = Nextcloud;\n\t\t\tpackageProductDependencies = (\n",
        f"\t\t\t);\n\t\t\tfileSystemSynchronizedGroups = (\n\t\t\t\t{group},\n\t\t\t);\n\t\t\tname = Nextcloud;\n\t\t\tpackageProductDependencies = (\n",
        path,
    )
    # No crash reports: the Crashlytics phase would upload the app's symbols to Firebase.
    text = replace(
        text,
        '\\"${BUILD_DIR%/Build/*}/SourcePackages/checkouts/firebase-ios-sdk/Crashlytics/run\\"',
        "# Imagina (IMAGINA.md): no crash reports to Firebase.\\nexit 0",
        path,
    )
    write(path, text)

    # Nextcloud's project copies its Firebase file (kept out of git) into the app: a placeholder, never used.
    firebase = ROOT / "GoogleService-Info.plist"
    if not firebase.exists():
        shutil.copyfile(IMAGINA / "GoogleService-Info.placeholder.plist", firebase)

    # Shared schemes name the extensions' bundle identifiers.
    for scheme in ("Share", "File Provider Extension", "BackgroundUploadExtension"):
        scheme_path = f"Nextcloud.xcodeproj/xcshareddata/xcschemes/{scheme}.xcscheme"
        scheme_text = upstream(scheme_path).decode()
        if "it.twsweb.Nextcloud" in scheme_text:
            scheme_text = scheme_text.replace("it.twsweb.Nextcloud.", f"{APP_ID}.").replace("it.twsweb.Nextcloud", APP_ID)
        write(scheme_path, scheme_text)


def brand_entitlements_and_plists() -> None:
    for entitlements in sorted((ROOT / "Brand").glob("*.entitlements")):
        path = str(entitlements.relative_to(ROOT))
        text = upstream(path).decode()
        text = text.replace("group.it.twsweb.Crypto-Cloud", GROUP)
        text = text.replace("$(AppIdentifierPrefix)it.twsweb.Crypto-Cloud", f"$(AppIdentifierPrefix){APP_ID}")
        text = text.replace("group.com.nextcloud.apps", f"{GROUP}.apps")
        if "twsweb" in text or "com.nextcloud" in text:
            raise BrandingError(f"{path}: an identifier of Nextcloud is left")
        write(path, text)

    path = "Brand/iOSClient.plist"
    text = upstream(path).decode()
    text = replace(text, "<key>CFBundleDisplayName</key>\n\t<string>Nextcloud</string>", f"<key>CFBundleDisplayName</key>\n\t<string>{APP_NAME}</string>", path)
    text = replace(text, "<key>CFBundleURLName</key>\n\t\t\t<string>it.twsweb.Nextcloud</string>", f"<key>CFBundleURLName</key>\n\t\t\t<string>{APP_ID}</string>", path)
    text = replace(text, "<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>nextcloud</string>", f"<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>{SCHEME}</string>", path)
    write(path, text)

    # Names in the Files app and the share sheet.
    for path in ("Brand/File_Provider_Extension.plist", "Brand/File_Provider_Extension_UI.plist", "Brand/Share.plist"):
        text = upstream(path).decode()
        text = replace(text, "<key>CFBundleDisplayName</key>\n\t<string>Nextcloud</string>", f"<key>CFBundleDisplayName</key>\n\t<string>{APP_NAME}</string>", path)
        text = text.replace("group.it.twsweb.Crypto-Cloud", GROUP)
        write(path, text)

    path = "Brand/Action_Assistant.plist"
    text = upstream(path).decode()
    text = replace(text, "<string>Nextcloud Assistant</string>", f"<string>{APP_NAME} Assistant</string>", path)
    write(path, text)


# ---------------------------------------------------------------------------------------------------
# Brand options (what Nextcloud lets a branded client change)

def brand_options() -> None:
    path = "Brand/NCBrand.swift"
    text = upstream(path).decode()
    cloud = P["IMAGINA_CLOUD_URL"]
    options = {
        r"var brand: String": swift_string(APP_NAME),
        r"var brandUserAgent: String": swift_string("Imagina"),
        r"var textCopyrightNextcloudiOS: String": swift_string(f"{APP_NAME} for iOS %@, based on Nextcloud (not the official app)"),
        r"var loginBaseUrl: String": swift_string(cloud),
        r"var pushNotificationServerProxy: String": swift_string(P.get("IMAGINA_PUSH_SERVER_URL", "")),
        r"var linkLoginHost: String": swift_string(cloud),
        r"var linkloginPreferredProviders: String": swift_string(cloud),
        r"var privacy: String": swift_string(P["IMAGINA_PRIVACY_URL"]),
        r"var sourceCode: String": swift_string(P["IMAGINA_SOURCE_CODE_URL"]),
        r"var appStoreUrl: String": swift_string(P["IMAGINA_APP_STORE_URL"]),
        r"var capabilitiesGroup: String": swift_string(GROUP),
        r"var capabilitiesGroupApps: String": swift_string(f"{GROUP}.apps"),
        # One fixed cloud, one account, no Nextcloud intro, links or crash reports.
        r"var disable_intro: Bool": "true",
        r"var disable_request_login_url: Bool": "true",
        r"var disable_multiaccount: Bool": "true",
        r"var disable_crash_service: Bool": "true",
        r"var disable_mobileconfig: Bool": "true",
        r"var disable_show_more_nextcloud_apps_in_settings: Bool": "true",
    }
    for pattern, value in options.items():
        text = set_line(text, pattern, value, path)

    red, green, blue = (int(P["IMAGINA_ACCENT"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    text = set_line(
        text,
        r"let customer: UIColor",
        f"UIColor(red: {red}.0 / 255.0, green: {green}.0 / 255.0, blue: {blue}.0 / 255.0, alpha: 1.0) // Imagina accent: {P['IMAGINA_ACCENT']}",
        path,
    )
    write(path, text)

    # The app's own links (widgets, deep links) use Imagina's scheme, so they never open the official app.
    path = "iOSClient/NCGlobal.swift"
    text = upstream(path).decode()
    text = replace(text, 'let appScheme                                   = "nextcloud"', f'let appScheme                                   = "{SCHEME}"', path)
    text = replace(text, '"nextcloud://open-action?', f'"{SCHEME}://open-action?', path, count=5)
    write(path, text)

    # Launch screen on Imagina's accent.
    path = "Brand/LaunchScreen.storyboard"
    text = upstream(path).decode()
    text = replace(
        text,
        'red="0.0" green="0.50980392156862742" blue="0.78823529411764703"',
        f'red="{red / 255:.17g}" green="{green / 255:.17g}" blue="{blue / 255:.17g}"',
        path,
    )
    write(path, text)


# ---------------------------------------------------------------------------------------------------
# «Entrar con Imagina» (imagina/Sources/ImaginaSignIn.swift) on Nextcloud's login screen

def hook_login() -> None:
    path = "iOSClient/Login/NCLogin.swift"
    text = upstream(path).decode()
    anchor = "        NCNetworking.shared.certificateDelegate = self\n    }\n"
    hook = (
        "        NCNetworking.shared.certificateDelegate = self\n"
        "\n"
        "        // Imagina (IMAGINA.md): «Entrar con Imagina» in place of the server address.\n"
        "        if ImaginaSignIn.isEnabled {\n"
        "            ImaginaSignIn.install(on: self, hiding: [baseUrlTextField, loginButton, loginAddressDetail, qrCode, certificate, enforceServersButton, enforceServersDropdownImage]) { [weak self] credentials in\n"
        "                await self?.createAccount(urlBase: credentials.server, user: credentials.user, password: credentials.appPassword)\n"
        "            }\n"
        "        }\n"
        "    }\n"
    )
    write(path, replace(text, anchor, hook, path))


def hook_menu() -> None:
    """«Configurar el correo de este iPhone» (imagina/Sources/ImaginaMailSetup.swift) in the Menu tab, above Settings."""
    path = "iOSClient/More/NCMoreModel.swift"
    text = upstream(path).decode()
    text = replace(
        text,
        "        /// No-op destination.\n        case none\n",
        "        /// Imagina (IMAGINA.md): an action of Imagina's own code.\n"
        "        case imagina(@MainActor () -> Void)\n"
        "\n"
        "        /// No-op destination.\n        case none\n",
        path,
    )
    text = replace(
        text,
        "        case .none:\n            break\n        }\n",
        "        case let .imagina(action):\n            action()\n\n        case .none:\n            break\n        }\n",
        path,
    )
    anchor = "        settingsItems.append(\n            Item(\n                titleKey: \"_settings_\","
    text = replace(
        text,
        anchor,
        "        // Imagina (IMAGINA.md): «Configurar el correo de este iPhone».\n"
        "        if let mailSetup = ImaginaMailSetup.menuItem(presentingFrom: controller) {\n"
        "            settingsItems.append(Item(titleKey: mailSetup.title, image: mailSetup.image, destination: .imagina(mailSetup.action)))\n"
        "        }\n"
        "\n" + anchor,
        path,
    )
    write(path, text)


def write_parameters() -> None:
    """imagina/Sources/ImaginaParameters.swift: the parameters the Imagina sources read. Generated, not in git."""
    values = {
        "applicationId": APP_ID,
        "cloudUrl": P["IMAGINA_CLOUD_URL"],
        "authHost": P.get("IMAGINA_AUTH_HOST", ""),
        "oauthClientId": P.get("IMAGINA_OAUTH_CLIENT_ID", ""),
        "testNextcloudUser": P.get("IMAGINA_TEST_NC_USER", ""),
        "testNextcloudAppPassword": P.get("IMAGINA_TEST_NC_APP_PASSWORD", ""),
        "testMailProfileUrl": P.get("IMAGINA_TEST_MAIL_PROFILE_URL", ""),
    }
    lines = [
        "// Generated by imagina/apply-branding.py from imagina/imagina.properties and imagina.local.properties.",
        "// Do not edit, and do not commit it (it can carry test credentials).",
        "",
        "enum ImaginaParameters {",
        *(f"    static let {name} = {swift_string(value)}" for name, value in values.items()),
        "}",
        "",
    ]
    (IMAGINA / "Sources" / "ImaginaParameters.swift").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------------------------------
# Images and texts

def brand_images() -> None:
    brand = IMAGINA / "brand"

    icon = ROOT / "AppIcon.icon"
    shutil.rmtree(icon)
    shutil.copytree(brand / "AppIcon.icon", icon)

    shutil.copyfile(brand / "AppIcon-1024.png", ROOT / "Brand/Custom.xcassets/AppIcon.appiconset/Icon-App-1024x1024@1x.png")
    shutil.copyfile(brand / "imagina-cloud-mark.svg", ROOT / "Brand/Custom.xcassets/logo.imageset/logo.svg")


def brand_texts() -> None:
    """The texts that name the app (not the server) say APP_NAME instead of «Nextcloud», in every language."""
    keys = ("_access_photo_not_enabled_msg_",)
    for strings in sorted((ROOT / "iOSClient/Supporting Files").glob("*.lproj/Localizable.strings")):
        path = str(strings.relative_to(ROOT))
        raw = upstream(path)
        encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
        text = raw.decode(encoding)
        lines = [
            line.replace("Nextcloud", APP_NAME) if line.lstrip().startswith(tuple(f'"{key}"' for key in keys)) else line
            for line in text.split("\n")
        ]
        strings.write_bytes("\n".join(lines).encode(encoding))


def main() -> int:
    try:
        brand_project()
        brand_entitlements_and_plists()
        brand_options()
        hook_login()
        hook_menu()
        write_parameters()
        brand_images()
        brand_texts()
    except BrandingError as error:
        print(f"apply-branding: {error}", file=sys.stderr)
        return 1
    print(f"Imagina Cloud branding applied on Nextcloud {TAG} ({APP_ID}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
