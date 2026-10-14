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
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
IMAGINA = ROOT / "imagina"


def read_parameters() -> tuple[dict, list[str]]:
    """(the parameters, the keys of imagina.local.properties that replace one of imagina.properties)."""
    parameters = {}
    overridden = []
    for name in ("imagina.properties", "imagina.local.properties"):
        path = IMAGINA / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if name == "imagina.local.properties" and key in parameters and parameters[key] != value.strip():
                    overridden.append(key)
                parameters[key] = value.strip()
    return parameters, overridden


P, LOCAL_OVERRIDES = read_parameters()
TAG = P["NEXTCLOUD_IOS_TAG"]
APP_ID = P["IMAGINA_APPLICATION_ID"]
APP_NAME = P["IMAGINA_APP_NAME"]
COPYRIGHT = P["IMAGINA_COPYRIGHT"]
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


def drop_object(text: str, object_id: str, path: str) -> str:
    """Removes the definition of a project object that spans several lines (from `ID /* name */ = {` to its closing `};`)."""
    pattern = re.compile(rf"\t\t{object_id} /\*[^\n]*\*/ = \{{\n.*?\n\t\t\}};\n", re.DOTALL)
    if len(pattern.findall(text)) != 1:
        raise BrandingError(f"{path}: expected the definition of the object {object_id} once")
    return pattern.sub("", text)


def drop_lines(text: str, object_id: str, count: int, path: str) -> str:
    """Removes the single lines of the project that start with an object's id: its one-line definition (a build file or a
    file reference) and its entry in the lists that name it."""
    pattern = re.compile(rf"^\t+{object_id} /\*[^\n]*(?:,|\}};)\n", re.MULTILINE)
    found = len(pattern.findall(text))
    if found != count:
        raise BrandingError(f"{path}: expected {count} line(s) for the object {object_id}, found {found}")
    return pattern.sub("", text)


def set_line(text: str, pattern: str, value: str, path: str) -> str:
    """Replaces the value of a single declaration line (`var name: Type = …`) keeping its indentation."""
    regex = re.compile(rf"^(\s*{pattern} = ).*$", re.MULTILINE)
    if len(regex.findall(text)) != 1:
        raise BrandingError(f"{path}: expected one line matching {pattern!r}")
    return regex.sub(lambda match: match.group(1) + value, text)


def swift_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def rgb(value: str) -> tuple[int, int, int]:
    """(red, green, blue) from `#RRGGBB`."""
    digits = value.lstrip("#")
    if len(digits) != 6:
        raise BrandingError(f"{value!r} is not a colour as #RRGGBB")
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def ui_color(value: str) -> str:
    red, green, blue = rgb(value)
    return f"UIColor(red: {red}.0 / 255.0, green: {green}.0 / 255.0, blue: {blue}.0 / 255.0, alpha: 1.0)"


def dynamic_ui_color(light: str, dark: str) -> str:
    """A UIColor that is `light` in the light theme and `dark` in the dark one."""
    return f"UIColor {{ $0.userInterfaceStyle == .dark ? {ui_color(dark)} : {ui_color(light)} }}"


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


# Appended to Brand/NCBrand.swift, which every target of the project compiles: the fonts are looked up by name and the
# system font takes their place where they are not bundled (only the app bundles Instrument Sans and Fraunces).
NC_BRAND_FONT = """
// MARK: - Imagina (IMAGINA.md)

/// Imagina's typefaces, Instrument Sans and Fraunces (`UIAppFonts` of iOSClient.plist), for the places that take their font
/// from the brand layer. Where the font is not bundled (the extensions) the system font takes its place. In the app, every
/// system font is already Instrument Sans (imagina/Sources/ImaginaFont.swift).
enum NCBrandFont {
    static func font(size: CGFloat, weight: UIFont.Weight = .regular, relativeTo textStyle: UIFont.TextStyle? = nil) -> UIFont {
        let name: String
        switch weight {
        case .bold, .heavy, .black:
            name = "InstrumentSans-Bold"
        case .semibold:
            name = "InstrumentSans-SemiBold"
        case .medium:
            name = "InstrumentSans-Medium"
        default:
            name = "InstrumentSans-Regular"
        }
        let font = UIFont(name: name, size: size) ?? UIFont.systemFont(ofSize: size, weight: weight)
        guard let textStyle else { return font }
        return UIFontMetrics(forTextStyle: textStyle).scaledFont(for: font)
    }

    /// Fraunces SemiBold (soft, optical size 24): the brand's face for big headlines and the title of an empty state, never
    /// for body text, buttons or labels. Scales with Dynamic Type like `textStyle`, up to `maximumPointSize`. Where the font
    /// is not bundled (the extensions) the system font takes its place.
    static func display(size: CGFloat, relativeTo textStyle: UIFont.TextStyle, maximumPointSize: CGFloat? = nil) -> UIFont {
        let font = UIFont(name: "Fraunces-SemiBold", size: size) ?? UIFont.systemFont(ofSize: size, weight: .semibold)
        let metrics = UIFontMetrics(forTextStyle: textStyle)
        guard let maximumPointSize else { return metrics.scaledFont(for: font) }
        return metrics.scaledFont(for: font, maximumPointSize: maximumPointSize)
    }
}
"""

# The usage descriptions iOS shows in its permission prompts, in Imagina's voice: they name the app and say plainly what each
# permission is for. Spanish is Spain's, tuteo; English is en-GB. The keys are those of Info.plist; the other languages keep
# Nextcloud's translations (the English text is also the Info.plist fallback).
_LOCATION_ES = "No usa el GPS y la ubicación no se envía a ningún sitio."
_LOCATION_EN = "It does not use GPS and your location is not sent anywhere."
PERMISSION_TEXTS = {
    "es": {
        "NSCameraUsageDescription": "Imagina Cloud usa la cámara para escanear documentos y hacer fotos o vídeos que subes a tu nube.",
        "NSMicrophoneUsageDescription": "Imagina Cloud usa el micrófono para grabar notas de voz y el sonido de los vídeos que haces, y guardarlos en tu nube.",
        "NSPhotoLibraryUsageDescription": "Imagina Cloud accede a tus fotos y vídeos para que elijas cuáles subir a tu nube y, si lo activas, subirlos automáticamente.",
        "NSPhotoLibraryAddUsageDescription": "Imagina Cloud guarda en tus fotos las imágenes y los vídeos que descargas de tu nube cuando se lo pides.",
        "NSFaceIDUsageDescription": "Imagina Cloud usa Face ID para desbloquear la app con tu cara si activas el código de acceso.",
        "NSLocationWhenInUseUsageDescription": f"Imagina Cloud usa tu ubicación solo para saber cuándo te mueves mucho y despertar la subida automática de tus fotos. {_LOCATION_ES}",
        "NSLocationAlwaysUsageDescription": f"Imagina Cloud usa tu ubicación, también en segundo plano, solo para despertar la subida automática de tus fotos cuando te mueves mucho. {_LOCATION_ES}",
        "NSLocationAlwaysAndWhenInUseUsageDescription": f"Imagina Cloud usa tu ubicación, también en segundo plano, solo para despertar la subida automática de tus fotos cuando te mueves mucho. {_LOCATION_ES}",
    },
    "en": {
        "NSCameraUsageDescription": "Imagina Cloud uses the camera to scan documents and to take photos or videos that you upload to your cloud.",
        "NSMicrophoneUsageDescription": "Imagina Cloud uses the microphone to record voice notes and the sound of the videos you take, and to save them to your cloud.",
        "NSPhotoLibraryUsageDescription": "Imagina Cloud accesses your photos and videos so that you can choose which ones to upload to your cloud and, if you turn it on, upload them automatically.",
        "NSPhotoLibraryAddUsageDescription": "Imagina Cloud saves to your photos the pictures and videos you download from your cloud when you ask it to.",
        "NSFaceIDUsageDescription": "Imagina Cloud uses Face ID to unlock the app with your face if you turn on the passcode.",
        "NSLocationWhenInUseUsageDescription": f"Imagina Cloud uses your location only to know when you move a long way and wake up the automatic upload of your photos. {_LOCATION_EN}",
        "NSLocationAlwaysUsageDescription": f"Imagina Cloud uses your location, in the background too, only to wake up the automatic upload of your photos when you move a long way. {_LOCATION_EN}",
        "NSLocationAlwaysAndWhenInUseUsageDescription": f"Imagina Cloud uses your location, in the background too, only to wake up the automatic upload of your photos when you move a long way. {_LOCATION_EN}",
    },
}

# The wordmark («imagina /cloud») is 240 pt wide in the app, whatever the SVG of the brand kit says: it only has a viewBox.
WORDMARK_WIDTH = 240.0


def wordmark_size() -> tuple[float, float]:
    """(width, height) in points of the wordmark in the asset catalog: 240 wide, the height of the brand kit's proportion."""
    source = (IMAGINA / "brand" / "imagina-cloud-wordmark.svg").read_text(encoding="utf-8")
    match = re.search(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"', source)
    if not match:
        raise BrandingError("imagina/brand/imagina-cloud-wordmark.svg has no viewBox")
    return WORDMARK_WIDTH, round(WORDMARK_WIDTH * float(match.group(2)) / float(match.group(1)), 2)


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

    # The App Store version and build number of the app and of every extension (they inherit the project's). Each upload to
    # App Store Connect needs a build number higher than the last one of the same version: raise IMAGINA_BUILD_NUMBER.
    for configuration, anchor_text in (("Debug", "F7F67BC91A24D27800EE80DA /* Debug */"), ("Release", "F7F67BCA1A24D27800EE80DA /* Release */")):
        for key, parameter, pattern in (
            ("MARKETING_VERSION", "IMAGINA_MARKETING_VERSION", r"\d+(\.\d+){0,2}"),
            ("CURRENT_PROJECT_VERSION", "IMAGINA_BUILD_NUMBER", r"\d+(\.\d+){0,2}"),
        ):
            value = P.get(parameter)
            if not value:
                continue
            if not re.fullmatch(pattern, value):
                raise BrandingError(f"{parameter} must be numbers separated by dots, not {value!r}")
            block = re.search(rf"\t\t{re.escape(anchor_text)} = \{{\n.*?\n\t\t\}};\n", text, re.DOTALL)
            if not block or len(re.findall(rf"\b{key} = [^;]+;", block.group(0))) != 1:
                raise BrandingError(f"{path}: expected one {key} in the project's {configuration} configuration")
            text = text.replace(block.group(0), re.sub(rf"\b{key} = [^;]+;", f"{key} = {value};", block.group(0)))

    # The widget extension's name (its Info.plist is generated from these keys), not «Nextcloud».
    text = replace(text, "INFOPLIST_KEY_CFBundleDisplayName = Nextcloud;", f'INFOPLIST_KEY_CFBundleDisplayName = "{APP_NAME}";', path, count=2)

    # Nextcloud's privacy manifest (the one its other extensions carry) also goes in the Action Assistant and the background
    # upload extension, which use the same required-reason APIs (UserDefaults, file dates) and ship without one.
    privacy_manifest = "F7E402282BA85D1D007E5609 /* PrivacyInfo.xcprivacy */"
    extension_manifests = (
        ("1A1B25C10D0000000000C002", "F7C55C782FB5AEF7004A974F"),  # Action Assistant, Resources phase
        ("1A1B25C10D0000000000C003", "F7FB187E30401D0D00EB0AE6"),  # BackgroundUploadExtension, Resources phase
    )
    for build_file, phase in extension_manifests:
        entry = f"{build_file} /* PrivacyInfo.xcprivacy in Resources */"
        text = replace(
            text,
            "/* End PBXBuildFile section */",
            f"\t\t{entry} = {{isa = PBXBuildFile; fileRef = {privacy_manifest}; }};\n/* End PBXBuildFile section */",
            path,
        )
        phase_head = f"\t\t{phase} /* Resources */ = {{\n\t\t\tisa = PBXResourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = (\n"
        text = replace(text, phase_head, phase_head + f"\t\t\t\t{entry},\n", path)

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

    # NSHumanReadableCopyright of the targets whose Info.plist Xcode generates (Widget, WidgetDashboardIntentHandler, Action
    # Assistant, BackgroundUploadExtension and the test bundles; the others carry it in their Info.plist: see
    # brand_entitlements_and_plists). It is set at project level, in the Debug and the Release configuration.
    text = replace(
        text,
        'INFOPLIST_KEY_NSHumanReadableCopyright = "Copyright © 2026 Nextcloud. All rights reserved.";',
        f"INFOPLIST_KEY_NSHumanReadableCopyright = {swift_string(COPYRIGHT)};",
        path,
        count=2,
    )

    # No Action Assistant in the app: it only hands selected text to the Nextcloud Assistant, which Imagina's server does not
    # have (app_api is off), so App Review would find an action that does nothing. The extension is neither embedded in the
    # app nor a dependency of its target, so no archive carries it. Its own target stays in the project, unbuilt by the app's
    # scheme, so a Nextcloud update that touches it still merges.
    text = drop_lines(text, "F7C55C882FB5AEF7004A974F", 2, path)  # Action Assistant.appex in Embed Foundation Extensions
    text = drop_object(text, "F7C55C872FB5AEF7004A974F", path)  # the app target's dependency on it
    text = drop_lines(text, "F7C55C872FB5AEF7004A974F", 1, path)
    text = drop_object(text, "F7C55C862FB5AEF7004A974F", path)  # the proxy of that dependency

    # No Firebase: the app sends no crash reports (disable_crash_service) and FirebaseApp.configure() is never called, so the
    # SDK was only dead weight in the binary (Core, Installations, Crashlytics, Sessions, GoogleDataTransport...) and its
    # resource bundles. Out go the package, its three product links (Crashlytics in the app; Database in the UI and
    # integration test bundles), the Crashlytics dSYM phase, and the GoogleService-Info.plist Nextcloud's project copies into
    # the app (kept out of git). The two Swift files that import it are edited by hook_app_delegate and brand_screens.
    for build_file in ("F3391B082B4C52C5001C0C4B", "F3391B162B4C52F6001C0C4B", "F70B86752642CE3B00ED5349"):  # Database, Database, Crashlytics
        text = drop_lines(text, build_file, 2, path)
    for product in ("F3391B072B4C52C5001C0C4B", "F3391B152B4C52F6001C0C4B", "F70B86742642CE3B00ED5349"):  # Database, Database, Crashlytics
        text = drop_object(text, product, path)
        text = drop_lines(text, product, 1, path)
    text = drop_object(text, "F70B86732642CE3B00ED5349", path)  # the firebase-ios-sdk package
    text = drop_lines(text, "F70B86732642CE3B00ED5349", 1, path)
    text = drop_object(text, "F76995F02F99EF6C00291FA7", path)  # Crashlytics dSYM Upload
    text = drop_lines(text, "F76995F02F99EF6C00291FA7", 1, path)
    text = drop_lines(text, "F7B8B83025681C3400967775", 2, path)  # GoogleService-Info.plist in Resources
    text = drop_lines(text, "F7B8B82F25681C3400967775", 2, path)  # GoogleService-Info.plist
    if re.search(r"firebase|crashlytics|GoogleService", text, re.IGNORECASE):
        raise BrandingError(f"{path}: something of Firebase is left in the project")
    write(path, text)

    # Shared schemes name the extensions' bundle identifiers.
    for scheme in ("Share", "File Provider Extension", "BackgroundUploadExtension"):
        scheme_path = f"Nextcloud.xcodeproj/xcshareddata/xcschemes/{scheme}.xcscheme"
        scheme_text = upstream(scheme_path).decode()
        if "it.twsweb.Nextcloud" in scheme_text:
            scheme_text = scheme_text.replace("it.twsweb.Nextcloud.", f"{APP_ID}.").replace("it.twsweb.Nextcloud", APP_ID)
        write(scheme_path, scheme_text)


def copyright_entry() -> str:
    """The NSHumanReadableCopyright entry of an Info.plist, with Imagina's text (see IMAGINA_COPYRIGHT)."""
    return f"\t<key>NSHumanReadableCopyright</key>\n\t<string>{escape(COPYRIGHT)}</string>\n"


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
    # The bundle's short name is the target's («Nextcloud») unless it is set: the app's own name, as Xcode's Organizer and
    # the system show it where the display name does not apply. The executable keeps Nextcloud's name.
    text = replace(text, "<key>CFBundleName</key>\n\t<string>$(PRODUCT_NAME)</string>", f"<key>CFBundleName</key>\n\t<string>{escape(APP_NAME)}</string>", path)
    text = replace(text, "<key>CFBundleURLName</key>\n\t\t\t<string>it.twsweb.Nextcloud</string>", f"<key>CFBundleURLName</key>\n\t\t\t<string>{APP_ID}</string>", path)
    text = replace(text, "<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>nextcloud</string>", f"<key>CFBundleURLSchemes</key>\n\t\t\t<array>\n\t\t\t\t<string>{SCHEME}</string>", path)
    # Instrument Sans and Fraunces (imagina/Sources/Fonts, bundled by the synchronized folder). Fonts of the app go in at the root of the bundle.
    fonts = "".join(f"\t\t<string>{font.name}</string>\n" for font in sorted((IMAGINA / "Sources" / "Fonts").glob("*.ttf")))
    if not fonts:
        raise BrandingError("imagina/Sources/Fonts has no font")
    text = replace(text, "\t<key>UIApplicationSceneManifest</key>\n", f"\t<key>UIAppFonts</key>\n\t<array>\n{fonts}\t</array>\n\t<key>UIApplicationSceneManifest</key>\n", path)
    # The launch screen is on the canvas (light or dark): the status bar follows the theme instead of staying light.
    text = replace(text, "<key>UIStatusBarStyle</key>\n\t<string>UIStatusBarStyleLightContent</string>", "<key>UIStatusBarStyle</key>\n\t<string>UIStatusBarStyleDefault</string>", path)
    # Export compliance: the code in Nextcloud's file was issued to Nextcloud for its documents, not to Imagina. The app does
    # use encryption beyond the system's (OpenSSL for end-to-end encryption), so ITSAppUsesNonExemptEncryption stays true; the
    # code is Imagina's own (IMAGINA_ENCRYPTION_COMPLIANCE_CODE, which App Store Connect gives once Imagina's export
    # documents are uploaded) or none, and then App Store Connect asks the export questions for each build.
    nextcloud_code = "\t<key>ITSEncryptionExportComplianceCode</key>\n\t<string>8e9f9874-938e-460b-a9be-f82cb3393971</string>\n"
    own_code = P.get("IMAGINA_ENCRYPTION_COMPLIANCE_CODE", "")
    if own_code and not re.fullmatch(r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", own_code):
        raise BrandingError("IMAGINA_ENCRYPTION_COMPLIANCE_CODE must be a UUID, as App Store Connect gives it")
    text = replace(text, nextcloud_code, f"\t<key>ITSEncryptionExportComplianceCode</key>\n\t<string>{own_code}</string>\n" if own_code else "", path)
    # The app and its extensions say «© Imagina», not Nextcloud (the generated Info.plists get it from the project's build settings).
    text = replace(text, "\t<key>NSAppTransportSecurity</key>\n", copyright_entry() + "\t<key>NSAppTransportSecurity</key>\n", path)
    # The usage descriptions of the permission prompts, in English as the fallback of every language without its own
    # (brand_permission_texts writes the localised ones).
    for key, value in PERMISSION_TEXTS["en"].items():
        text, found = re.subn(rf"(<key>{key}</key>\n\t<string>)[^<]*(</string>)", lambda match: match.group(1) + escape(value) + match.group(2), text)
        if found != 1:
            raise BrandingError(f"{path}: expected one {key}, found {found}")
    write(path, text)

    # Names in the Files app and the share sheet.
    for path in ("Brand/File_Provider_Extension.plist", "Brand/File_Provider_Extension_UI.plist", "Brand/Share.plist"):
        text = upstream(path).decode()
        text = replace(text, "<key>CFBundleDisplayName</key>\n\t<string>Nextcloud</string>", f"<key>CFBundleDisplayName</key>\n\t<string>{APP_NAME}</string>", path)
        text = text.replace("group.it.twsweb.Crypto-Cloud", GROUP)
        if path.endswith("File_Provider_Extension_UI.plist"):
            # It already carries an empty NSHumanReadableCopyright.
            text = replace(text, "<key>NSHumanReadableCopyright</key>\n\t<string></string>\n", copyright_entry().lstrip("\t"), path)
        else:
            text = replace(text, "\t<key>NSAppTransportSecurity</key>\n", copyright_entry() + "\t<key>NSAppTransportSecurity</key>\n", path)
        write(path, text)

    # The notification service extension (its Info.plist has no copyright yet).
    path = "Brand/Notification_Service_Extension.plist"
    text = upstream(path).decode()
    text = replace(text, "\t<key>NSExtension</key>\n", copyright_entry() + "\t<key>NSExtension</key>\n", path)
    write(path, text)

    path = "Brand/Action_Assistant.plist"
    text = upstream(path).decode()
    text = replace(text, "<string>Nextcloud Assistant</string>", f"<string>{APP_NAME} Assistant</string>", path)
    write(path, text)

    # Nextcloud's demo cloud as the base URL of the background upload extension: no reference to it is left.
    path = "Brand/BackgroundUploadExtension.plist"
    text = upstream(path).decode()
    text = replace(text, "<string>https://cloud.nextcloud.com</string>", f"<string>{P['IMAGINA_CLOUD_URL']}</string>", path)
    write(path, text)


# ---------------------------------------------------------------------------------------------------
# Brand options (what Nextcloud lets a branded client change)

def brand_options() -> None:
    path = "Brand/NCBrand.swift"
    text = upstream(path).decode()
    cloud = P["IMAGINA_CLOUD_URL"]
    if not cloud.startswith("https://"):
        raise BrandingError(f"IMAGINA_CLOUD_URL must be an https URL, not {cloud!r}")
    # Imagina's push server (C7.10/C11.5) speaks Nextcloud's push proxy protocol; the app registers its APNs token there
    # through the Nextcloud server. Empty: no notifications.
    push = P.get("IMAGINA_PUSH_SERVER_URL", "").rstrip("/")
    if push and not push.startswith("https://"):
        raise BrandingError(f"IMAGINA_PUSH_SERVER_URL must be an https URL, not {push!r}")
    source_code = P["IMAGINA_SOURCE_CODE_URL"]
    if not source_code.startswith("https://"):
        raise BrandingError(f"IMAGINA_SOURCE_CODE_URL must be an https URL (the GPL asks for it), not {source_code!r}")
    options = {
        r"var brand: String": swift_string(APP_NAME),
        r"var brandUserAgent: String": swift_string("Imagina"),
        # Shown at the foot of Settings: it says the app is modified and not Nextcloud's own.
        r"var textCopyrightNextcloudiOS: String": swift_string(f"{APP_NAME} for iOS %@, a modified version of Nextcloud for iOS (not the official app)"),
        r"var loginBaseUrl: String": swift_string(cloud),
        r"var pushNotificationServerProxy: String": swift_string(push),
        r"var linkLoginHost: String": swift_string(cloud),
        r"var linkloginPreferredProviders: String": swift_string(cloud),
        r"var privacy: String": swift_string(P["IMAGINA_PRIVACY_URL"]),
        r"var sourceCode: String": swift_string(source_code),
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
        # The link to the source code (GPL) stays in Settings.
        r"var disable_source_code_in_settings: Bool": "false",
    }
    for pattern, value in options.items():
        text = set_line(text, pattern, value, path)

    text = set_line(
        text,
        r"let customer: UIColor",
        f"{ui_color(P['IMAGINA_ACCENT'])} // Imagina accent: {P['IMAGINA_ACCENT']}",
        path,
    )
    # `customer` is the accent and only that: the screens the brand paints (launch, sign-in, the Files app's error, the
    # maintenance screens) are on the canvas with ink text, and so are the main screens (see brand_screens).
    text = replace(
        text,
        "    var customerText: UIColor = .white\n",
        "    var customerText: UIColor = .white\n"
        "\n"
        "    // Imagina (IMAGINA.md): `customer` above is the accent (teal), only for highlights. Screens are on the canvas (cream) with\n"
        "    // ink text; both change with the dark theme.\n"
        f"    let customerBackground: UIColor = {dynamic_ui_color(P['IMAGINA_CANVAS'], P['IMAGINA_CANVAS_DARK'])}\n"
        f"    let customerBackgroundText: UIColor = {dynamic_ui_color(P['IMAGINA_INK'], P['IMAGINA_INK_DARK'])}\n",
        path,
    )
    text += NC_BRAND_FONT
    write(path, text)

    # The app's own links (widgets, deep links) use Imagina's scheme, so they never open the official app.
    path = "iOSClient/NCGlobal.swift"
    text = upstream(path).decode()
    text = replace(text, 'let appScheme                                   = "nextcloud"', f'let appScheme                                   = "{SCHEME}"', path)
    text = replace(text, '"nextcloud://open-action?', f'"{SCHEME}://open-action?', path, count=5)
    write(path, text)

    # Launch screen on the canvas (the named colour ImaginaCanvas, light and dark in Custom.xcassets) with the wordmark.
    path = "Brand/LaunchScreen.storyboard"
    text = upstream(path).decode()
    canvas_red, canvas_green, canvas_blue = rgb(P["IMAGINA_CANVAS"])
    text = replace(
        text,
        '<color key="backgroundColor" red="0.0" green="0.50980392156862742" blue="0.78823529411764703" alpha="1" colorSpace="custom" customColorSpace="sRGB"/>',
        '<color key="backgroundColor" name="ImaginaCanvas"/>',
        path,
    )
    text = replace(
        text,
        '        <capability name="Safe area layout guides" minToolsVersion="9.0"/>\n',
        '        <capability name="Named colors" minToolsVersion="9.0"/>\n        <capability name="Safe area layout guides" minToolsVersion="9.0"/>\n',
        path,
    )
    width, height = wordmark_size()
    text = replace(
        text,
        '<rect key="frame" x="59.5" y="269.5" width="256" height="128"/>',
        f'<rect key="frame" x="{(375 - width) / 2:g}" y="{(667 - height) / 2:g}" width="{width:g}" height="{height:g}"/>',
        path,
    )
    text = replace(
        text,
        '        <image name="logo" width="256" height="128"/>\n',
        f'        <image name="logo" width="{width:g}" height="{height:g}"/>\n'
        '        <namedColor name="ImaginaCanvas">\n'
        f'            <color red="{canvas_red / 255:.17g}" green="{canvas_green / 255:.17g}" blue="{canvas_blue / 255:.17g}" alpha="1" colorSpace="custom" customColorSpace="sRGB"/>\n'
        '        </namedColor>\n',
        path,
    )
    write(path, text)


# ---------------------------------------------------------------------------------------------------
# «Entrar con Imagina» (imagina/Sources/ImaginaSignIn.swift) on Nextcloud's login screen

def hook_login() -> None:
    path = "iOSClient/Login/NCLogin.swift"
    text = upstream(path).decode()
    # The screen is on the canvas (cream), not on the brand colour: its texts and tints follow from the canvas.
    text = replace(text, "NCBrandColor.shared.customer", "NCBrandColor.shared.customerBackground", path, count=5)
    anchor = "        NCNetworking.shared.certificateDelegate = self\n    }\n"
    hook = (
        "        NCNetworking.shared.certificateDelegate = self\n"
        "\n"
        "        // Imagina (IMAGINA.md): the wordmark and «Entrar con Imagina» in place of the logo and the server address.\n"
        "        if ImaginaSignIn.isEnabled {\n"
        "            ImaginaSignIn.install(on: self, hiding: [imageBrand, baseUrlTextField, loginButton, loginAddressDetail, qrCode, certificate, enforceServersButton, enforceServersDropdownImage]) { [weak self] credentials in\n"
        "                await self?.createAccount(urlBase: credentials.server, user: credentials.user, password: credentials.appPassword)\n"
        "            }\n"
        "        }\n"
        "    }\n"
    )
    write(path, replace(text, anchor, hook, path))


def hook_menu() -> None:
    """«Configurar el correo» (imagina/Sources/ImaginaMailSetup.swift) in the Menu tab, above Settings. The row appears
    while this iPhone is a connected device; `reload` builds the Menu again when the state of the profile changes. And the
    «Actividad» row only where the server has the activity app."""
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
        "        if let mailSetup = ImaginaMailSetup.menuItem(presentingFrom: controller, reload: { [weak self] in Task { await self?.loadItems() } }) {\n"
        "            settingsItems.append(Item(titleKey: mailSetup.title, image: mailSetup.image, destination: .imagina(mailSetup.action)))\n"
        "        }\n"
        "\n" + anchor,
        path,
    )
    # «Actividad» only where the server offers the activity app: Imagina's Nextcloud does not have it (deploy/nextcloud/setup.sh
    # turns it off), so the screen could only be empty. Nextcloud's own file details already hide their Activity tab the same way.
    activity_row = (
        "        functionItems.append(\n"
        "            Item(\n"
        "                titleKey: \"_activity_\",\n"
        "                image: \"bolt.fill\",\n"
        "                destination: .storyboard(\n"
        "                    name: \"NCActivity\",\n"
        "                    presentation: .push\n"
        "                )\n"
        "            )\n"
        "        )\n"
    )
    text = replace(
        text,
        activity_row,
        "        // Imagina (IMAGINA.md): only when the server has the activity app.\n"
        "        if !capabilities.activity.isEmpty {\n"
        + "".join(f"    {line}\n" for line in activity_row.splitlines())
        + "        }\n",
        path,
    )
    write(path, text)


def hook_account_removal() -> None:
    """The person removes the account in the app: this iPhone is disconnected from Imagina too (best effort)."""
    path = "iOSClient/Account/Account Settings/NCAccountSettingsModel.swift"
    text = upstream(path).decode()
    anchor = "                await NCAccount().deleteAccount(tblAccount.account)\n"
    text = replace(
        text,
        anchor,
        anchor
        + "                // Imagina (IMAGINA.md): this iPhone is no longer a device connected to Imagina either.\n"
        + "                ImaginaDevice.disconnect()\n",
        path,
    )
    write(path, text)


def hook_app_delegate() -> None:
    """The notices of new mail (imagina/Sources/ImaginaPush.swift and ImaginaMailNotice.swift, C12.6): the app's APNs token
    also goes to Imagina's devices API, and a tap on Imagina's notice opens the message in Mail before Nextcloud looks at
    the response. Nextcloud's own notifications are not touched. And Imagina's look (ImaginaTheme: the typeface, the canvas and
    the tab bar's titles), installed when the app starts. And no Firebase: its import and its configuration go."""
    path = "iOSClient/AppDelegate.swift"
    text = upstream(path).decode()

    # No Firebase (see brand_project): the crash reporting it served is off in this app, and the package is not linked.
    text = replace(text, "import Firebase\n", "", path)
    text = replace(
        text,
        "        if !NCPreferences().disableCrashservice, !NCBrandOptions.shared.disable_crash_service {\n            FirebaseApp.configure()\n        }\n\n",
        "        // Imagina (IMAGINA.md): no Firebase and no crash reports.\n\n",
        path,
    )

    anchor = "    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {\n"
    text = replace(
        text,
        anchor,
        anchor
        + "        // Imagina (IMAGINA.md): Instrument Sans for every system font, the canvas for the system's page backgrounds, the tab bar.\n"
        + "        ImaginaTheme.install()\n"
        + "\n",
        path,
    )

    anchor = "    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {\n"
    text = replace(
        text,
        anchor,
        anchor
        + "        // Imagina (IMAGINA.md): the token also goes to Imagina, for the notices of new mail.\n"
        + "        ImaginaPush.tokenArrived(deviceToken)\n"
        + "\n",
        path,
    )

    anchor = "    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {\n"
    text = replace(
        text,
        anchor,
        anchor
        + "        // Imagina (IMAGINA.md): a tap on a notice of new mail opens that message in Mail.\n"
        + "        if ImaginaMailNotice.handle(response) {\n"
        + "            completionHandler()\n"
        + "            return\n"
        + "        }\n"
        + "\n",
        path,
    )
    write(path, text)


def hook_tab_bar() -> None:
    """The bottom tab bar of the iPhone takes the adaptive accent (`#0F766E`; `#2DD4BF` in the dark theme), the same as the iPad's
    floating bar, which takes the window's tint (ImaginaTheme.install). Nextcloud tinted it with the server theme's colour, a
    single colour for both themes."""
    path = "iOSClient/Main/NCMainTabBarController.swift"
    text = upstream(path).decode()
    text = replace(
        text,
        "tabBar.tintColor = NCBrandColor.shared.getElement(account: account)",
        "tabBar.tintColor = ImaginaColor.accent // Imagina (IMAGINA.md): the adaptive accent",
        path,
        count=2,
    )
    write(path, text)


def hook_settings_footer() -> None:
    """The foot of Settings says what the app is in the person's language (`ImaginaText.appNotice` and `serverNotice`), not in
    the English of NCBrand's `textCopyrightNextcloudiOS` and `textCopyrightNextcloudServer` (which stay as they are for the
    logs of the app and its extensions)."""
    path = "iOSClient/Settings/Settings/NCSettingsModel.swift"
    text = upstream(path).decode()
    text = replace(
        text,
        '        footerApp = String(format: NCBrandOptions.shared.textCopyrightNextcloudiOS, NCUtility().getVersionBuild()) + "\\n\\n"\n'
        '        footerServer = String(format: NCBrandOptions.shared.textCopyrightNextcloudServer, capabilities.serverVersion) + "\\n"\n',
        "        // Imagina (IMAGINA.md): the notices of the foot of Settings in the person's language.\n"
        '        footerApp = ImaginaText.appNotice(version: NCUtility().getVersionBuild()) + "\\n\\n"\n'
        '        footerServer = ImaginaText.serverNotice(version: capabilities.serverVersion) + "\\n"\n',
        path,
    )
    write(path, text)


def hook_photos_prompt() -> None:
    """No Photos prompt before the person uses a photo feature. On iOS 27 the app calls `disableIfIdle` every time it becomes
    active and that touches PhotoKit, which makes iOS ask for the photo library on the very first launch, before sign-in and
    out of context. It now does nothing until access to Photos has already been given (the picker, auto upload and the other
    photo features ask for it themselves, when the person uses them)."""
    path = "BackgroundUploadExtension/NCBackgroundUploadExtensionManager.swift"
    text = upstream(path).decode()
    anchor = "    func disableIfIdle() async -> Bool {\n"
    text = replace(
        text,
        anchor,
        anchor
        + "        // Imagina (IMAGINA.md): PhotoKit is not touched (and Photos is not asked for) until access has been given.\n"
        + "        let photosAccess = PHPhotoLibrary.authorizationStatus(for: .readWrite)\n"
        + "        guard photosAccess == .authorized || photosAccess == .limited else {\n"
        + "            return true\n"
        + "        }\n"
        + "\n",
        path,
    )
    write(path, text)


def brand_notifications() -> None:
    """The notification service extension names the app, not Nextcloud, when it cannot read a notification."""
    path = "Notification Service Extension/NotificationService.swift"
    text = upstream(path).decode()
    text = replace(text, 'bestAttemptContent.body = "Nextcloud notification"', 'bestAttemptContent.body = "\\(NCBrandOptions.shared.brand) notification"', path)
    write(path, text)


def write_parameters() -> None:
    """imagina/Sources/ImaginaParameters.swift: the parameters the Imagina sources read. Generated, not in git."""
    if P.get("IMAGINA_AUTH_HOST") and not P.get("IMAGINA_OAUTH_CLIENT_ID"):
        raise BrandingError("IMAGINA_AUTH_HOST is set but IMAGINA_OAUTH_CLIENT_ID is not")
    values = {
        "applicationId": APP_ID,
        "cloudUrl": P["IMAGINA_CLOUD_URL"],
        "authHost": P.get("IMAGINA_AUTH_HOST", ""),
        "oauthClientId": P.get("IMAGINA_OAUTH_CLIENT_ID", ""),
    }
    lines = [
        "// Generated by imagina/apply-branding.py from imagina/imagina.properties and imagina.local.properties.",
        "// Do not edit, and do not commit it (git ignores it).",
        "",
        "enum ImaginaParameters {",
        *(f"    static let {name} = {swift_string(value)}" for name, value in values.items()),
        "}",
        "",
    ]
    (IMAGINA / "Sources" / "ImaginaParameters.swift").write_text("\n".join(lines), encoding="utf-8")


def brand_screens() -> None:
    """Screens on the canvas (cream, with ink text) where Nextcloud paints the brand colour as a background, and the main
    screens (files, media, Menu) and bars on the canvas instead of the system's white. Settings, the sheets and the other
    lists get it from ImaginaCanvas (imagina/Sources/ImaginaBrand.swift). Teal stays as the accent: the tints, the buttons,
    the switches and the selection come from the theme of the server (`color-element`, teal) as before."""
    background = "NCBrandColor.shared.customerBackground"
    ink = "NCBrandColor.shared.customerBackgroundText"

    # The web fallback of the login (Imagina never reaches it: its sign-in is Imagina's own).
    path = "iOSClient/Login/NCLoginProvider.swift"
    text = upstream(path).decode()
    text = replace(text, "        view.backgroundColor = NCBrandColor.shared.customer\n", f"        view.backgroundColor = {background}\n", path)
    text = replace(text, "        closeButton.tintColor = .white\n", f"        closeButton.tintColor = {ink}\n", path)
    write(path, text)

    # The error screen of the Files app's extension.
    path = "File Provider Extension UI/DocumentActionViewController.swift"
    text = upstream(path).decode()
    text = replace(text, "        view.backgroundColor = NCBrandColor.shared.customer\n", f"        view.backgroundColor = {background}\n", path)
    text = replace(text, "        titleError.textColor = NCBrandColor.shared.customerText\n", f"        titleError.textColor = {ink}\n", path)
    text = replace(text, "cancelButton.setTitleColor(NCBrandColor.shared.customerText, for: .normal)", f"cancelButton.setTitleColor({ink}, for: .normal)", path)
    write(path, text)

    # The screens shown while the database is compacted at a new version (also the first launch) and migrated.
    path = "iOSClient/Utility/Maintenance.swift"
    text = upstream(path).decode()
    text = replace(text, "Color(NCBrandColor.shared.customer)", f"Color({background})", path)
    text = replace(text, ".foregroundColor(.white)", f".foregroundColor(Color({ink}))", path, count=2)
    text = replace(text, "CircularProgressViewStyle(tint: .white)", "CircularProgressViewStyle(tint: Color(NCBrandColor.shared.customer))", path)
    write(path, text)

    path = "iOSClient/Utility/MigrationMultiDomains.swift"
    text = upstream(path).decode()
    text = replace(text, "Color(NCBrandColor.shared.customer)", f"Color({background})", path)
    text = replace(text, ".foregroundColor(.white)", f".foregroundColor(Color({ink}))", path, count=3)
    text = replace(text, "LinearProgressViewStyle(tint: .white)", "LinearProgressViewStyle(tint: Color(NCBrandColor.shared.customer))", path)
    write(path, text)

    # Navigation bars: the canvas (before iOS 26, which draws its own) and Instrument Sans in the title and the text buttons.
    path = "iOSClient/Extensions/UINavigationController+Extension.swift"
    text = upstream(path).decode()
    text = replace(text, "backgroundColor: UIColor? = .systemBackground) {", f"backgroundColor: UIColor? = {background}) {{", path)
    text = replace(
        text,
        "        appearance.titleTextAttributes = [.foregroundColor: textColor]\n",
        "        // Imagina (IMAGINA.md): Instrument Sans in the title and the text buttons.\n"
        "        appearance.titleTextAttributes = [.foregroundColor: textColor, .font: NCBrandFont.font(size: 17, weight: .semibold)]\n"
        "        appearance.buttonAppearance.normal.titleTextAttributes = [.font: NCBrandFont.font(size: 17, weight: .regular)]\n"
        "        appearance.doneButtonAppearance.normal.titleTextAttributes = [.font: NCBrandFont.font(size: 17, weight: .semibold)]\n",
        path,
    )
    write(path, text)

    # Files, Favorites, Offline, Shares and the rest of the lists that share NCCollectionViewCommon.
    path = "iOSClient/Main/Collection Common/NCCollectionViewCommon.swift"
    text = upstream(path).decode()
    text = replace(
        text,
        "        view.backgroundColor = .systemBackground\n        collectionView.backgroundColor = .systemBackground\n",
        f"        view.backgroundColor = {background}\n        collectionView.backgroundColor = {background}\n",
        path,
    )
    write(path, text)

    path = "iOSClient/Media/NCMedia.swift"
    text = upstream(path).decode()
    text = replace(text, "        view.backgroundColor = .systemBackground\n", f"        view.backgroundColor = {background}\n", path)
    text = replace(text, "        collectionView.backgroundColor = .systemBackground\n", f"        collectionView.backgroundColor = {background}\n", path)
    write(path, text)

    # The Menu tab: the canvas behind its white cards.
    path = "iOSClient/More/NCMoreView.swift"
    text = upstream(path).decode()
    text = replace(text, "Color(.systemGroupedBackground)", f"Color({background})", path, count=3)
    write(path, text)

    # Trash, the notifications and the folder picker, which paint the system's white.
    for path, count in (
        ("iOSClient/Trash/NCTrash.swift", 2),
        ("iOSClient/Notification/NCNotification.swift", 2),
        ("iOSClient/Select/NCSelect.swift", 3),
    ):
        text = upstream(path).decode()
        text = replace(text, "backgroundColor = .systemBackground\n", f"backgroundColor = {background}\n", path, count=count)
        write(path, text)

    # A file's details and sharing, which paint the grouped grey.
    for path, count in (("iOSClient/Share/NCSharePaging.swift", 3), ("iOSClient/Share/NCShare.swift", 2)):
        text = upstream(path).decode()
        text = replace(text, "backgroundColor = .systemGroupedBackground\n", f"backgroundColor = {background}\n", path, count=count)
        write(path, text)

    # Activity (also inside a file's details, where Nextcloud uses the grouped grey).
    path = "iOSClient/Activity/NCActivity.swift"
    text = upstream(path).decode()
    text = replace(text, "usesGroupedBackground ? .systemGroupedBackground : .systemBackground", background, path, count=2)
    write(path, text)

    # Settings and its screens (SwiftUI): their Form and List on the canvas through ImaginaForm and ImaginaList
    # (imagina/Sources/ImaginaBrand.swift), which hide the system's grouped grey behind them.
    for path, form, plain in (
        ("iOSClient/Settings/Display/NCDisplayView.swift", 1, 0),
        ("iOSClient/Settings/AutoUpload/NCAutoUploadView.swift", 1, 0),
        ("iOSClient/Settings/Advanced/NCSettingsAdvancedView.swift", 1, 0),
        ("iOSClient/Settings/Advanced/File Name/NCFileNameView.swift", 1, 0),
        ("iOSClient/Settings/Advanced/NCLogFilesView.swift", 0, 1),
        ("iOSClient/Settings/Advanced/Capabilities/NCCapabilitiesView.swift", 0, 1),
        ("iOSClient/Settings/E2EE/NCManageE2EEView.swift", 0, 2),
        ("iOSClient/Settings/SelectAlbum/SelectAlbumView.swift", 0, 1),
    ):
        text = upstream(path).decode()
        if form:
            text = replace(text, " Form {\n", " ImaginaForm {\n", path, count=form)
        if plain:
            text = replace(text, " List {\n", " ImaginaList {\n", path, count=plain)
        write(path, text)

    # The Menu's navigation bar is `.systemGray6`.
    path = "iOSClient/More/NCMoreNavigationController.swift"
    text = upstream(path).decode()
    text = replace(text, "setNavigationBarAppearance(backgroundColor: .systemGray6)", f"setNavigationBarAppearance(backgroundColor: {background})", path)
    write(path, text)

    # The foot of Settings, where the app says what it is: the wordmark above the notice.
    path = "iOSClient/Settings/Settings/NCSettingsView.swift"
    text = upstream(path).decode()
    # No Firebase (see brand_project): its Crashlytics log in the Debug section's test crash goes.
    text = replace(text, "import FirebaseCrashlytics\n", "", path)
    text = replace(text, '                    Crashlytics.crashlytics().log("Test crash triggered")\n', "", path)
    # Its Form on the canvas, as the other screens of Settings (see above).
    text = replace(text, " Form {\n", " ImaginaForm {\n", path)
    text = replace(
        text,
        "                Text(model.footerApp + model.footerServer + model.footerSlogan)\n                    .font(.footnote)\n",
        "                // Imagina (IMAGINA.md): the wordmark above the notice of the app.\n"
        "                ImaginaAboutFooter(text: model.footerApp + model.footerServer + model.footerSlogan)\n",
        path,
    )
    write(path, text)

    # The title of an empty state («Sin archivos»…): Fraunces, as the brand book asks for EmptyState titles (the one place
    # every empty list of the app shares: Files, Favorites, Trash, the folder picker…).
    path = "iOSClient/Main/Collection Common/Section Header Footer/NCSectionFirstHeaderEmptyData.swift"
    text = upstream(path).decode()
    text = replace(
        text,
        "        emptyTitle.font = .headline()\n",
        "        // Imagina (IMAGINA.md): the title of an empty state in Fraunces.\n"
        "        emptyTitle.font = NCBrandFont.display(size: 20, relativeTo: .title3, maximumPointSize: 28)\n",
        path,
    )
    write(path, text)


# The families bundled in imagina/Sources/Fonts, under the SIL Open Font License 1.1 (LICENSES/OFL-1.1.txt): glob, repository
# and copyright line of each (the lines the brand kit's fonts carry in their name tables).
FONT_FAMILIES = (
    ("Instrument Sans", "InstrumentSans-*.ttf", "https://github.com/Instrument/instrument-sans", "2022 The Instrument Sans Project Authors (https://github.com/Instrument/instrument-sans)"),
    ("Fraunces", "Fraunces-*.ttf", "https://github.com/undercasetype/Fraunces", "2020 The Fraunces Project Authors (github.com/undercasetype/Fraunces)"),
)


def brand_licences() -> None:
    """The fonts are under the SIL Open Font License: REUSE needs to know (REUSE.toml), and so do the people who use the app
    (the «Agradecimientos» screen of Settings shows Acknowledgements.rtf)."""
    path = "REUSE.toml"
    text = upstream(path).decode()
    text = text.rstrip("\n") + "\n"
    for name, glob, _repository, copyright_line in FONT_FAMILIES:
        text += (
            "\n"
            f"# Imagina Cloud (IMAGINA.md): {name}, a typeface of the brand, bundled in the app.\n"
            "[[annotations]]\n"
            f'path = ["imagina/Sources/Fonts/{glob}"]\n'
            'precedence = "aggregate"\n'
            f'SPDX-FileCopyrightText = "{copyright_line}"\n'
            'SPDX-License-Identifier = "OFL-1.1"\n'
        )
    write(path, text)

    # Acknowledgements.rtf is what the screen shows (its text, not its formatting): Nextcloud's file plus the fonts, in the same
    # layout (`\\` and a line break is a paragraph). It is cp1252: read and written byte for byte.
    path = "iOSClient/Settings/Acknowledgements.rtf"
    text = upstream(path).decode("latin-1")
    separator = "__________________________________\\\n"
    block = ""
    for name, _glob, repository, copyright_line in FONT_FAMILIES:
        holders = copyright_line.split(" (")[0]
        block += f"\\\n\\f1\\b {name}\n\\f0\\b0 \\\n\\\n{repository}\\\n\\\nSIL Open Font License 1.1\\\n\\\nCopyright {holders}\\\n{separator}"
    text = replace(text, separator + "}", separator + block + "}", path)
    (ROOT / path).write_bytes(text.encode("latin-1"))


# ---------------------------------------------------------------------------------------------------
# Images and texts

def brand_images() -> None:
    brand = IMAGINA / "brand"

    icon = ROOT / "AppIcon.icon"
    shutil.rmtree(icon)
    shutil.copytree(brand / "AppIcon.icon", icon)

    shutil.copyfile(brand / "AppIcon-1024.png", ROOT / "Brand/Custom.xcassets/AppIcon.appiconset/Icon-App-1024x1024@1x.png")

    # `logo` is the wordmark («imagina /cloud»), which Nextcloud's screens (launch, sign-in, the Files app's error) and
    # Imagina's (Settings) show where Nextcloud had its logo: dark-ink on the canvas, ivory on the dark canvas. The SVGs of the
    # brand kit only have a viewBox: the copies in the catalog also say their size, so the image is 240 pt wide.
    width, height = wordmark_size()
    logo = ROOT / "Brand/Custom.xcassets/logo.imageset"
    for source, filename in (("imagina-cloud-wordmark.svg", "logo.svg"), ("imagina-cloud-wordmark-reverse.svg", "logo-dark.svg")):
        svg = (brand / source).read_text(encoding="utf-8")
        svg = replace(svg, '<svg xmlns="http://www.w3.org/2000/svg" ', f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height:g}" ', source)
        (logo / filename).write_text(svg, encoding="utf-8")
    (logo / "Contents.json").write_text(
        json.dumps(
            {
                "images": [
                    {"filename": "logo.svg", "idiom": "universal"},
                    {"appearances": [{"appearance": "luminosity", "value": "dark"}], "filename": "logo-dark.svg", "idiom": "universal"},
                ],
                "info": {"author": "xcode", "version": 1},
                "properties": {"preserves-vector-representation": True},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # The canvas for the launch screen (a storyboard takes its colours from the catalog), light and dark.
    def components(value: str) -> dict:
        red, green, blue = rgb(value)
        return {"alpha": "1.000", "blue": f"0x{blue:02X}", "green": f"0x{green:02X}", "red": f"0x{red:02X}"}

    canvas = ROOT / "Brand/Custom.xcassets/ImaginaCanvas.colorset"
    canvas.mkdir(exist_ok=True)
    (canvas / "Contents.json").write_text(
        json.dumps(
            {
                "colors": [
                    {"color": {"color-space": "srgb", "components": components(P["IMAGINA_CANVAS"])}, "idiom": "universal"},
                    {
                        "appearances": [{"appearance": "luminosity", "value": "dark"}],
                        "color": {"color-space": "srgb", "components": components(P["IMAGINA_CANVAS_DARK"])},
                        "idiom": "universal",
                    },
                ],
                "info": {"author": "xcode", "version": 1},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# Imagina's own wording of Nextcloud's strings: imagina/l10n/<language>.lproj/<table>.strings, the same `"key" = "value";`
# format as the file it changes. Where Nextcloud keeps each table for a language folder.
L10N = IMAGINA / "l10n"
L10N_TABLES = {
    "Localizable.strings": "iOSClient/Supporting Files/{lproj}/Localizable.strings",
    "Localizable.stringsdict": "iOSClient/Supporting Files/{lproj}/Localizable.stringsdict",
    "Intent.strings": "Widget/Intent/{lproj}/Intent.strings",
}
# An entry of a .stringsdict (the plural forms): from `\t<key>name</key>` to the closing `\t</dict>` of its own dict.
STRINGSDICT_ENTRY = re.compile(r"^\t<key>(?P<key>[^<]+)</key>\n\t<dict>\n.*?\n\t</dict>\n", re.DOTALL | re.MULTILINE)
STRINGS_ENTRY = re.compile(r'^(?P<head>\s*"(?P<key>(?:[^"\\]|\\.)*)"\s*=\s*)"(?P<value>(?:[^"\\]|\\.)*)"(?P<tail>\s*;.*)$')
# What a translation has to keep exactly: printf specifiers (%@, %d, %1$d, %%…) and the ${placeholders} of Intent.strings.
STRINGS_PLACEHOLDER = re.compile(r"%(?:\d+\$)?[-+ 0#]*(?:\d+|\*)?(?:\.\d+)?(?:hh|h|ll|l|L|q|z|t|j)?[@dDiuUxXoOfeEgGcCsSpaAF%]|\$\{[^}]*\}")


def read_strings(raw: bytes) -> tuple[str, str]:
    """(the text of a .strings file, its encoding): UTF-16 when it has a byte order mark, UTF-8 otherwise."""
    encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
    return raw.decode(encoding), encoding


def l10n_overrides() -> dict[str, dict[str, str]]:
    """The overrides in imagina/l10n by the file of Nextcloud they change: {path: {key: value}} (values as written in the
    file, escapes included, with {{app_name}} replaced by the app's name)."""
    overrides: dict[str, dict[str, str]] = {}
    for file in sorted(L10N.glob("*.lproj/*.strings*")):
        relative = str(file.relative_to(ROOT))
        if file.name not in L10N_TABLES:
            raise BrandingError(f"{relative}: Nextcloud's file for the table {file.name} is not known (L10N_TABLES)")
        target = L10N_TABLES[file.name].format(lproj=file.parent.name)
        entries: dict[str, str] = {}
        if file.suffix == ".stringsdict":
            for entry in STRINGSDICT_ENTRY.finditer(file.read_text(encoding="utf-8")):
                if entry.group("key") in entries:
                    raise BrandingError(f"{relative}: the key {entry.group('key')} is twice")
                entries[entry.group("key")] = entry.group(0).replace("{{app_name}}", APP_NAME)
            if not entries:
                raise BrandingError(f"{relative}: no entry found")
            overrides[target] = entries
            continue
        in_comment = False
        for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if in_comment:
                in_comment = "*/" not in stripped
                continue
            if not stripped or stripped.startswith("//"):
                continue
            if stripped.startswith("/*"):
                in_comment = "*/" not in stripped
                continue
            entry = STRINGS_ENTRY.match(line)
            if not entry or entry.group("tail").strip() != ";":
                raise BrandingError(f"{relative}:{number}: expected one `\"key\" = \"value\";` per line")
            if entry.group("key") in entries:
                raise BrandingError(f"{relative}:{number}: the key {entry.group('key')} is twice")
            entries[entry.group("key")] = entry.group("value").replace("{{app_name}}", APP_NAME)
        overrides[target] = entries
    return overrides


def merge_overrides(text: str, overrides: dict[str, str], path: str) -> str:
    """Nextcloud's strings file with the value of each overridden key replaced (every line of the key, if Nextcloud repeats
    it) and everything else as it was. Stops when a key is not there any more or a translation loses or changes a specifier."""
    found: set[str] = set()
    lines = []
    for line in text.split("\n"):
        entry = STRINGS_ENTRY.match(line)
        if entry and entry.group("key") in overrides:
            key = entry.group("key")
            if sorted(STRINGS_PLACEHOLDER.findall(entry.group("value"))) != sorted(STRINGS_PLACEHOLDER.findall(overrides[key])):
                raise BrandingError(f"{path}: the override of {key} does not keep the specifiers of Nextcloud's text ({entry.group('value')!r})")
            found.add(key)
            line = f'{entry.group("head")}"{overrides[key]}"{entry.group("tail")}'
        lines.append(line)
    missing = sorted(set(overrides) - found)
    if missing:
        raise BrandingError(f"{path}: Nextcloud's file no longer has {', '.join(missing)} (imagina/l10n): review those overrides")
    return "\n".join(lines)


def merge_stringsdict_overrides(text: str, overrides: dict[str, str], path: str) -> str:
    """The same for a .stringsdict: the whole entry (all its plural forms) of each overridden key is replaced."""
    found: set[str] = set()

    def replace_entry(entry: re.Match) -> str:
        key = entry.group("key")
        if key not in overrides:
            return entry.group(0)
        if set(STRINGS_PLACEHOLDER.findall(entry.group(0))) != set(STRINGS_PLACEHOLDER.findall(overrides[key])):
            raise BrandingError(f"{path}: the override of {key} does not keep the specifiers of Nextcloud's entry")
        found.add(key)
        return overrides[key]

    text = STRINGSDICT_ENTRY.sub(replace_entry, text)
    missing = sorted(set(overrides) - found)
    if missing:
        raise BrandingError(f"{path}: Nextcloud's file no longer has {', '.join(missing)} (imagina/l10n): review those overrides")
    return text


def brand_texts() -> None:
    """The texts that name the app (not the server) say APP_NAME instead of «Nextcloud», in every language, and Imagina's
    own wording (imagina/l10n: Spanish of Spain in «tú») replaces Nextcloud's where it is written."""
    keys = ("_access_photo_not_enabled_msg_",)
    overrides = l10n_overrides()
    for strings in sorted((ROOT / "iOSClient/Supporting Files").glob("*.lproj/Localizable.strings")):
        path = str(strings.relative_to(ROOT))
        text, encoding = read_strings(upstream(path))
        lines = [
            line.replace("Nextcloud", APP_NAME) if line.lstrip().startswith(tuple(f'"{key}"' for key in keys)) else line
            for line in text.split("\n")
        ]
        text = "\n".join(lines)
        if path in overrides:
            text = merge_overrides(text, overrides.pop(path), path)
        strings.write_bytes(text.encode(encoding))
    # The other tables: the plural forms and the widgets' configuration screen.
    for path, entries in sorted(overrides.items()):
        text, encoding = read_strings(upstream(path))
        merge = merge_stringsdict_overrides if path.endswith(".stringsdict") else merge_overrides
        (ROOT / path).write_bytes(merge(text, entries, path).encode(encoding))


def brand_permission_texts() -> None:
    """The usage descriptions of the permission prompts (camera, microphone, Photos, Face ID, location) name Imagina Cloud and
    say what each is for, in Spanish (Spain) and English (en and en-GB); the other languages keep Nextcloud's text."""
    for folder, texts in (("es", PERMISSION_TEXTS["es"]), ("en", PERMISSION_TEXTS["en"]), ("en-GB", PERMISSION_TEXTS["en"])):
        path = f"iOSClient/Supporting Files/{folder}.lproj/InfoPlist.strings"
        raw = upstream(path)
        encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
        text = raw.decode(encoding)
        for key, value in texts.items():
            text, found = re.subn(rf'^({key}\s*=\s*)"[^"\n]*"', lambda match: match.group(1) + json.dumps(value, ensure_ascii=False), text, flags=re.MULTILINE)
            if found != 1:
                raise BrandingError(f"{path}: expected one {key}, found {found}")
        (ROOT / path).write_bytes(text.encode(encoding))


def main() -> int:
    try:
        brand_project()
        brand_entitlements_and_plists()
        brand_options()
        hook_login()
        hook_menu()
        hook_account_removal()
        hook_app_delegate()
        hook_photos_prompt()
        hook_tab_bar()
        hook_settings_footer()
        brand_screens()
        brand_licences()
        brand_notifications()
        write_parameters()
        brand_images()
        brand_texts()
        brand_permission_texts()
    except BrandingError as error:
        print(f"apply-branding: {error}", file=sys.stderr)
        return 1
    print(f"Imagina Cloud branding applied on Nextcloud {TAG} ({APP_ID}).")
    if LOCAL_OVERRIDES:
        print(f"Note: imagina.local.properties replaces {', '.join(LOCAL_OVERRIDES)}: not for a build that goes to TestFlight or the App Store.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
