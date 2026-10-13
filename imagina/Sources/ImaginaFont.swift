// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import ObjectiveC
import SwiftUI
import UIKit

/// Instrument Sans in place of San Francisco across the app (Imagina's brand book: Instrument Sans for all UI text).
///
/// Nextcloud sets its fonts label by label (111 fonts in xibs and storyboards, some 350 SwiftUI `.font(…)` and a few UIKit
/// calls), so instead of editing each of them Imagina swaps the factories everything goes through (installed when the app
/// starts, `ImaginaTheme.install()`):
///
/// - `UIFont.systemFont(ofSize:)`, `systemFont(ofSize:weight:)`, `boldSystemFont(ofSize:)`, `preferredFont(forTextStyle:)` (with
///   and without a trait collection) and the system fonts a nib or storyboard decodes (`UIFont(coder:)`) give Instrument Sans at
///   the same size and the nearest weight (400, 500, 600 or 700; lighter is 400). On iOS 27 UIKit's own text (alerts, bars,
///   default label fonts) and SwiftUI's system fonts ask for their fonts through these too.
/// - SwiftUI's text styles `Font.body`, `.headline`, `.footnote`… as Nextcloud's code (another module than SwiftUI) writes them
///   are Imagina's: a declaration with the same name in this module shadows SwiftUI's, so `.font(.body)` and `.cappedFont(.body)`
///   (Nextcloud's helper) are Instrument Sans scaling with Dynamic Type whatever the iOS version does, with no line changed
///   upstream.
///
/// Not touched: monospaced, rounded and italic system fonts, `monospacedDigitSystemFont`, SF Symbols (images; `.icon()`,
/// `Font.system(size:)` and the symbol configurations keep drawing them as before) and what the system draws with its own fonts
/// (the keyboard, the share sheet, context menus). Glyphs the font lacks (beyond Latin and Latin Extended) fall back to the
/// system font as usual.
///
/// `replacesSystemFont` is the switch: `false` leaves San Francisco wherever Nextcloud asks for the system font. The places
/// that name Instrument Sans themselves (sign-in, bars, Settings' foot) keep it either way.
enum ImaginaFont {
    static let replacesSystemFont = true

    /// PostScript name of the bundled face nearest to `weight` (Thin to Light are Regular: the family has no lighter one).
    static func faceName(for weight: UIFont.Weight) -> String {
        switch weight.rawValue {
        case 0.35...: return "InstrumentSans-Bold"
        case 0.27...: return "InstrumentSans-SemiBold"
        case 0.12...: return "InstrumentSans-Medium"
        default: return "InstrumentSans-Regular"
        }
    }

    /// The system font (San Francisco's regular, not its monospaced, rounded, condensed or italic designs).
    private static func isSystemFont(_ font: UIFont) -> Bool {
        let name = font.fontName
        guard name.hasPrefix(".SF") || name.hasPrefix(".AppleSystemUIFont") else { return false }
        return !["Mono", "Rounded", "Condensed", "Compact", "Italic", "Expanded"].contains { name.contains($0) }
    }

    private static func weight(of font: UIFont) -> UIFont.Weight {
        let traits = font.fontDescriptor.object(forKey: .traits) as? [UIFontDescriptor.TraitKey: Any]
        guard let value = (traits?[.weight] as? NSNumber)?.doubleValue else { return .regular }
        return UIFont.Weight(rawValue: CGFloat(value))
    }

    /// Instrument Sans for the system `font` Nextcloud (or UIKit) asked for: the same size and the nearest weight. For a text
    /// style it is the size UIKit gives the system font of that style now (Dynamic Type already applied), as a plain font:
    /// Nextcloud scales it again with `UIFontMetrics` where it wants a cap (`UIFont+Extension.swift`), which UIKit refuses to
    /// do to a font that `UIFontMetrics` itself returned. Any other font, or Instrument Sans missing from the bundle, comes
    /// back as it is.
    fileprivate static func replacement(for font: UIFont) -> UIFont {
        guard replacesSystemFont, !isScaling, isSystemFont(font) else { return font }
        return UIFont(name: faceName(for: weight(of: font)), size: font.pointSize) ?? font
    }

    /// Instrument Sans for a font a nib decodes. If Interface Builder gave the font a text style (Body, Footnote…) it keeps it:
    /// scaled with `UIFontMetrics` from the size of the style at the default content size, so a label that adjusts its font
    /// follows Dynamic Type while the app runs, as it did in San Francisco.
    fileprivate static func replacement(forDecoded font: UIFont) -> UIFont {
        let plain = replacement(for: font)
        guard plain !== font, let name = font.fontDescriptor.object(forKey: .textStyle) as? String else { return plain }
        let style = UIFont.TextStyle(rawValue: name)
        let defaultSize = UITraitCollection(preferredContentSizeCategory: .large)
        guard publicTextStyles.contains(style),
              let base = UIFont(name: plain.fontName, size: UIFont.preferredFont(forTextStyle: style, compatibleWith: defaultSize).pointSize) else { return plain }
        return UIFontMetrics(forTextStyle: style).scaledFont(for: base)
    }

    private static let publicTextStyles: [UIFont.TextStyle] = [.largeTitle, .title1, .title2, .title3, .headline, .subheadline, .body, .callout, .footnote, .caption1, .caption2]

    /// The size and weight of each text style in San Francisco at the default content size (Large): SwiftUI scales Instrument
    /// Sans from them as it does the style (`Font.custom(_:size:relativeTo:)`).
    private static let swiftUIStyles: [Font.TextStyle: (size: CGFloat, weight: UIFont.Weight)] = [
        .largeTitle: (34, .regular),
        .title: (28, .regular),
        .title2: (22, .regular),
        .title3: (20, .regular),
        .headline: (17, .semibold),
        .subheadline: (15, .regular),
        .body: (17, .regular),
        .callout: (16, .regular),
        .footnote: (13, .regular),
        .caption: (12, .regular),
        .caption2: (11, .regular)
    ]

    /// A text style as SwiftUI's `Font`: Instrument Sans scaling with Dynamic Type relative to the style, or the system's.
    fileprivate static func swiftUI(_ textStyle: Font.TextStyle) -> Font {
        guard replacesSystemFont, let style = swiftUIStyles[textStyle] else { return .system(textStyle) }
        return .custom(faceName(for: style.weight), size: style.size, relativeTo: textStyle)
    }

    // MARK: Swizzling

    private static var isInstalled = false

    /// Called once when the app starts (`ImaginaTheme.install()`).
    @MainActor
    static func install() {
        guard replacesSystemFont, !isInstalled else { return }
        isInstalled = true
        exchange(NSSelectorFromString("systemFontOfSize:"), NSSelectorFromString("imagina_systemFontOfSize:"))
        exchange(NSSelectorFromString("systemFontOfSize:weight:"), NSSelectorFromString("imagina_systemFontOfSize:weight:"))
        exchange(NSSelectorFromString("boldSystemFontOfSize:"), NSSelectorFromString("imagina_boldSystemFontOfSize:"))
        exchange(NSSelectorFromString("preferredFontForTextStyle:"), NSSelectorFromString("imagina_preferredFontForTextStyle:"))
        exchange(NSSelectorFromString("preferredFontForTextStyle:compatibleWithTraitCollection:"), NSSelectorFromString("imagina_preferredFontForTextStyle:compatibleWithTraitCollection:"))
        replaceDecodedFonts()
        guardFontMetrics()
    }

    // MARK: UIFontMetrics

    private static let scalingKey = "imagina.font.scaling"

    /// `UIFontMetrics` is working: UIKit asks the factories for the system font of a text style to know how much to scale a
    /// font, and has to get that system font, not Instrument Sans (a font without the style would not be scaled at all).
    private static var isScaling: Bool {
        Thread.current.threadDictionary[scalingKey] != nil
    }

    private static func whileScaling<T>(_ body: () -> T) -> T {
        let dictionary = Thread.current.threadDictionary
        let outer = dictionary[scalingKey]
        dictionary[scalingKey] = true
        defer {
            if let outer { dictionary[scalingKey] = outer } else { dictionary.removeObject(forKey: scalingKey) }
        }
        return body()
    }

    /// Every public way to scale a font or a value with `UIFontMetrics` runs inside `whileScaling`.
    private static func guardFontMetrics() {
        func implementation(_ selector: Selector) -> (Method, IMP)? {
            guard let method = class_getInstanceMethod(UIFontMetrics.self, selector) else { return nil }
            return (method, method_getImplementation(method))
        }

        typealias Font = @convention(c) (AnyObject, Selector, UIFont) -> UIFont
        typealias FontCapped = @convention(c) (AnyObject, Selector, UIFont, CGFloat) -> UIFont
        typealias FontTraits = @convention(c) (AnyObject, Selector, UIFont, UITraitCollection?) -> UIFont
        typealias FontCappedTraits = @convention(c) (AnyObject, Selector, UIFont, CGFloat, UITraitCollection?) -> UIFont
        typealias Value = @convention(c) (AnyObject, Selector, CGFloat) -> CGFloat
        typealias ValueTraits = @convention(c) (AnyObject, Selector, CGFloat, UITraitCollection?) -> CGFloat

        let fontSelector = NSSelectorFromString("scaledFontForFont:")
        if let (method, imp) = implementation(fontSelector) {
            let original = unsafeBitCast(imp, to: Font.self)
            let block: @convention(block) (AnyObject, UIFont) -> UIFont = { metrics, font in
                whileScaling { original(metrics, fontSelector, font) }
            }
            method_setImplementation(method, imp_implementationWithBlock(block))
        }
        let cappedSelector = NSSelectorFromString("scaledFontForFont:maximumPointSize:")
        if let (method, imp) = implementation(cappedSelector) {
            let original = unsafeBitCast(imp, to: FontCapped.self)
            let block: @convention(block) (AnyObject, UIFont, CGFloat) -> UIFont = { metrics, font, maximum in
                whileScaling { original(metrics, cappedSelector, font, maximum) }
            }
            method_setImplementation(method, imp_implementationWithBlock(block))
        }
        let traitsSelector = NSSelectorFromString("scaledFontForFont:compatibleWithTraitCollection:")
        if let (method, imp) = implementation(traitsSelector) {
            let original = unsafeBitCast(imp, to: FontTraits.self)
            let block: @convention(block) (AnyObject, UIFont, UITraitCollection?) -> UIFont = { metrics, font, traits in
                whileScaling { original(metrics, traitsSelector, font, traits) }
            }
            method_setImplementation(method, imp_implementationWithBlock(block))
        }
        let cappedTraitsSelector = NSSelectorFromString("scaledFontForFont:maximumPointSize:compatibleWithTraitCollection:")
        if let (method, imp) = implementation(cappedTraitsSelector) {
            let original = unsafeBitCast(imp, to: FontCappedTraits.self)
            let block: @convention(block) (AnyObject, UIFont, CGFloat, UITraitCollection?) -> UIFont = { metrics, font, maximum, traits in
                whileScaling { original(metrics, cappedTraitsSelector, font, maximum, traits) }
            }
            method_setImplementation(method, imp_implementationWithBlock(block))
        }
        let valueSelector = NSSelectorFromString("scaledValueForValue:")
        if let (method, imp) = implementation(valueSelector) {
            let original = unsafeBitCast(imp, to: Value.self)
            let block: @convention(block) (AnyObject, CGFloat) -> CGFloat = { metrics, value in
                whileScaling { original(metrics, valueSelector, value) }
            }
            method_setImplementation(method, imp_implementationWithBlock(block))
        }
        let valueTraitsSelector = NSSelectorFromString("scaledValueForValue:compatibleWithTraitCollection:")
        if let (method, imp) = implementation(valueTraitsSelector) {
            let original = unsafeBitCast(imp, to: ValueTraits.self)
            let block: @convention(block) (AnyObject, CGFloat, UITraitCollection?) -> CGFloat = { metrics, value, traits in
                whileScaling { original(metrics, valueTraitsSelector, value, traits) }
            }
            method_setImplementation(method, imp_implementationWithBlock(block))
        }
    }

    /// The fonts a nib or storyboard decodes (`-[UIFont initWithCoder:]`): Interface Builder's system fonts, by size, weight or
    /// text style, come from here and not from the factories above. `init…` returns an owned object: the original's answer is
    /// released when another font takes its place.
    private static func replaceDecodedFonts() {
        let selector = NSSelectorFromString("initWithCoder:")
        guard let method = class_getInstanceMethod(UIFont.self, selector) else { return }
        typealias Original = @convention(c) (AnyObject, Selector, NSCoder) -> Unmanaged<UIFont>?
        let original = unsafeBitCast(method_getImplementation(method), to: Original.self)
        let replacement: @convention(block) (AnyObject, NSCoder) -> Unmanaged<UIFont>? = { receiver, coder in
            guard let owned = original(receiver, selector, coder) else { return nil }
            let decoded = owned.takeUnretainedValue()
            let font = ImaginaFont.replacement(forDecoded: decoded)
            guard font !== decoded else { return owned }
            owned.release()
            return Unmanaged.passRetained(font)
        }
        method_setImplementation(method, imp_implementationWithBlock(replacement))
    }

    private static func exchange(_ original: Selector, _ replacement: Selector) {
        guard let originalMethod = class_getClassMethod(UIFont.self, original),
              let replacementMethod = class_getClassMethod(UIFont.self, replacement) else { return }
        method_exchangeImplementations(originalMethod, replacementMethod)
    }
}

// After `ImaginaFont.install()` each `imagina_…` method below holds UIKit's own implementation and the UIKit name holds this
// one: calling `imagina_…` from its replacement is the call to UIKit.
extension UIFont {
    @objc(imagina_systemFontOfSize:)
    class func imagina_systemFont(ofSize fontSize: CGFloat) -> UIFont {
        ImaginaFont.replacement(for: imagina_systemFont(ofSize: fontSize))
    }

    @objc(imagina_systemFontOfSize:weight:)
    class func imagina_systemFont(ofSize fontSize: CGFloat, weight: UIFont.Weight) -> UIFont {
        ImaginaFont.replacement(for: imagina_systemFont(ofSize: fontSize, weight: weight))
    }

    @objc(imagina_boldSystemFontOfSize:)
    class func imagina_boldSystemFont(ofSize fontSize: CGFloat) -> UIFont {
        ImaginaFont.replacement(for: imagina_boldSystemFont(ofSize: fontSize))
    }

    @objc(imagina_preferredFontForTextStyle:)
    class func imagina_preferredFont(forTextStyle style: UIFont.TextStyle) -> UIFont {
        ImaginaFont.replacement(for: imagina_preferredFont(forTextStyle: style))
    }

    @objc(imagina_preferredFontForTextStyle:compatibleWithTraitCollection:)
    class func imagina_preferredFont(forTextStyle style: UIFont.TextStyle, compatibleWith traitCollection: UITraitCollection?) -> UIFont {
        ImaginaFont.replacement(for: imagina_preferredFont(forTextStyle: style, compatibleWith: traitCollection))
    }
}

// SwiftUI's text styles, shadowed in this module (see ImaginaFont): the declarations are named and typed as SwiftUI's own.
extension Font {
    static var largeTitle: Font { ImaginaFont.swiftUI(.largeTitle) }
    static var title: Font { ImaginaFont.swiftUI(.title) }
    static var title2: Font { ImaginaFont.swiftUI(.title2) }
    static var title3: Font { ImaginaFont.swiftUI(.title3) }
    static var headline: Font { ImaginaFont.swiftUI(.headline) }
    static var subheadline: Font { ImaginaFont.swiftUI(.subheadline) }
    static var body: Font { ImaginaFont.swiftUI(.body) }
    static var callout: Font { ImaginaFont.swiftUI(.callout) }
    static var footnote: Font { ImaginaFont.swiftUI(.footnote) }
    static var caption: Font { ImaginaFont.swiftUI(.caption) }
    static var caption2: Font { ImaginaFont.swiftUI(.caption2) }
}
