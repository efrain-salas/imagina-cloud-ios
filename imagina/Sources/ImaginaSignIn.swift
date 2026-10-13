// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import AuthenticationServices
import CryptoKit
import UIKit

/// «Entrar con Imagina»: instead of Nextcloud's server address and login pages, the person signs in with Imagina
/// (mobile number and SMS code) in a web sheet that closes by itself. Imagina's devices API then creates this iPhone
/// as a device and hands the app the Nextcloud login only this device has. Off unless `IMAGINA_AUTH_HOST` is set in
/// imagina/imagina.properties.
///
/// This is also the screen Nextcloud's own check of the login ends in when Imagina disconnects the device: the app
/// removes the account and shows the login, which here is this button.
@MainActor
final class ImaginaSignIn: NSObject {
    typealias Credentials = ImaginaCredentials

    static var isEnabled: Bool { !ImaginaParameters.authHost.isEmpty }

    private enum Step {
        case signIn
        case connect
    }

    private weak var screen: UIViewController?
    private let onSignedIn: (Credentials) async -> Void
    private var button: UIButton?

    private init(screen: UIViewController, onSignedIn: @escaping (Credentials) async -> Void) {
        self.screen = screen
        self.onSignedIn = onSignedIn
    }

    /// Puts the wordmark and the «Entrar con Imagina» button on Nextcloud's login screen in place of its logo and the
    /// server address. The screen is on the canvas (cream), where Nextcloud's login code paints the brand colour;
    /// teal is only the button. The button keeps this object alive through its action.
    static func install(on screen: UIViewController, hiding views: [UIView?], onSignedIn: @escaping (Credentials) async -> Void) {
        let signIn = ImaginaSignIn(screen: screen, onSignedIn: onSignedIn)
        views.forEach { $0?.isHidden = true }

        // The wordmark («imagina /cloud»), not the icon: this screen has room for it.
        let wordmark = UIImageView(image: UIImage(named: "logo"))
        wordmark.contentMode = .scaleAspectFit
        wordmark.isAccessibilityElement = true
        wordmark.accessibilityLabel = NCBrandOptions.shared.brand
        wordmark.accessibilityTraits = .image

        var configuration = UIButton.Configuration.filled()
        configuration.title = ImaginaText.signIn
        configuration.baseBackgroundColor = ImaginaColor.accent
        configuration.baseForegroundColor = ImaginaColor.onAccent
        configuration.cornerStyle = .fixed
        configuration.background.cornerRadius = 12
        configuration.buttonSize = .large
        configuration.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { incoming in
            var outgoing = incoming
            outgoing.font = NCBrandFont.font(size: 17, weight: .semibold, relativeTo: .body)
            return outgoing
        }

        let button = UIButton(configuration: configuration, primaryAction: UIAction { _ in signIn.start(from: .signIn) })
        button.accessibilityIdentifier = "imaginaSignIn"

        let hint = UILabel()
        hint.text = ImaginaText.signInHint
        hint.font = NCBrandFont.font(size: 13, weight: .regular, relativeTo: .footnote)
        hint.adjustsFontForContentSizeCategory = true
        hint.textColor = ImaginaColor.inkSecondary
        hint.textAlignment = .center
        hint.numberOfLines = 0

        let stack = UIStackView(arrangedSubviews: [wordmark, button, hint])
        stack.axis = .vertical
        stack.alignment = .center
        stack.setCustomSpacing(56, after: wordmark)
        stack.setCustomSpacing(12, after: button)
        stack.translatesAutoresizingMaskIntoConstraints = false
        screen.view.addSubview(stack)

        let safeArea = screen.view.safeAreaLayoutGuide
        let width = stack.widthAnchor.constraint(equalToConstant: 300)
        width.priority = .defaultHigh
        var constraints = [
            stack.centerXAnchor.constraint(equalTo: safeArea.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: safeArea.centerYAnchor, constant: -24),
            stack.leadingAnchor.constraint(greaterThanOrEqualTo: safeArea.leadingAnchor, constant: 32),
            stack.trailingAnchor.constraint(lessThanOrEqualTo: safeArea.trailingAnchor, constant: -32),
            width,
            button.widthAnchor.constraint(equalTo: stack.widthAnchor),
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: 50),
            hint.widthAnchor.constraint(equalTo: stack.widthAnchor),
            wordmark.widthAnchor.constraint(lessThanOrEqualTo: stack.widthAnchor)
        ]
        if let size = wordmark.image?.size, size.width > 0 {
            constraints.append(wordmark.heightAnchor.constraint(equalTo: wordmark.widthAnchor, multiplier: size.height / size.width))
        }
        NSLayoutConstraint.activate(constraints)
        signIn.button = button
    }

    // MARK: - Sign-in

    private func start(from step: Step) {
        Task { await run(from: step) }
    }

    /// Web sheet, then the device, then Nextcloud's account. A refusal of Imagina is shown with its own words and a
    /// way to try again from the step that failed (the tokens of a sign-in that worked are not asked for again).
    private func run(from firstStep: Step) async {
        var step = firstStep
        setBusy(true)
        defer { setBusy(false) }

        do {
            if step == .signIn {
                guard try await ImaginaAuthorization.signIn(from: screen?.view.window) == .signedIn else { return }
                step = .connect
            }
            let credentials = try await ImaginaDevice.connect()
            await onSignedIn(credentials)
            // The notices of new mail (C12.6) need the permission for alerts; the token is already on its way to Imagina.
            ImaginaPush.requestPermissionIfUndecided()
            Task { await ImaginaMailSetup.offerAfterSignIn() }
        } catch {
            let failure = error as? ImaginaFailure ?? .unexpected
            if case .needsSignIn = failure {
                step = .signIn
            }
            showFailure(failure, retrying: step)
        }
    }

    // MARK: - Screen

    private func setBusy(_ busy: Bool) {
        button?.configuration?.showsActivityIndicator = busy
        button?.isEnabled = !busy
    }

    private func showFailure(_ failure: ImaginaFailure, retrying step: Step) {
        let alert = UIAlertController(title: ImaginaText.signInFailedTitle, message: failure.message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: ImaginaText.cancel, style: .cancel))
        let retry = UIAlertAction(title: ImaginaText.retry, style: .default) { [weak self] _ in
            self?.start(from: step)
        }
        alert.addAction(retry)
        alert.preferredAction = retry
        screen?.present(alert, animated: true)
    }
}

// MARK: - OAuth

/// OAuth 2.0 authorization code with PKCE against Imagina's OIDC server (public client), in an ephemeral web
/// session. The scope is `openid cloud.devices`: the tokens only serve to manage this iPhone's device. Its tokens
/// are kept in the Keychain (`ImaginaStore`).
@MainActor
final class ImaginaAuthorization: NSObject {
    enum Outcome {
        case signedIn
        /// The person closed the sheet.
        case cancelled
    }

    private let window: UIWindow?
    private var session: ASWebAuthenticationSession?

    private init(window: UIWindow?) {
        self.window = window
    }

    /// Shows Imagina's sign-in. When it works, the tokens are in the Keychain.
    static func signIn(from window: UIWindow?) async throws -> Outcome {
        try await ImaginaAuthorization(window: window).run()
    }

    private func run() async throws -> Outcome {
        let verifier = Self.randomToken()
        let state = Self.randomToken()

        var components = URLComponents()
        components.scheme = "https"
        components.host = ImaginaParameters.authHost
        components.path = "/oauth/authorize"
        components.queryItems = [
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "client_id", value: ImaginaParameters.oauthClientId),
            URLQueryItem(name: "redirect_uri", value: Self.redirectUri),
            URLQueryItem(name: "scope", value: "openid cloud.devices"),
            URLQueryItem(name: "state", value: state),
            URLQueryItem(name: "code_challenge", value: Self.challenge(of: verifier)),
            URLQueryItem(name: "code_challenge_method", value: "S256")
        ]
        guard let url = components.url else { throw ImaginaFailure.unexpected }

        let callbackUrl = try await authorize(url)
        defer { session = nil }
        guard let callbackUrl else { return .cancelled }

        guard let items = URLComponents(url: callbackUrl, resolvingAgainstBaseURL: false)?.queryItems,
              items.first(where: { $0.name == "state" })?.value == state,
              let code = items.first(where: { $0.name == "code" })?.value else {
            throw ImaginaFailure.unexpected
        }

        let tokens = try await ImaginaHTTP.requestTokens(
            [
                ("grant_type", "authorization_code"),
                ("client_id", ImaginaParameters.oauthClientId),
                ("redirect_uri", Self.redirectUri),
                ("code", code),
                ("code_verifier", verifier)
            ],
            rejection: .unexpected
        )
        await ImaginaApi.shared.store(tokens)
        return .signedIn
    }

    /// The URL the sheet returns to, or nil when the person cancelled it.
    private func authorize(_ url: URL) async throws -> URL? {
        try await withCheckedThrowingContinuation { continuation in
            let completion: ASWebAuthenticationSession.CompletionHandler = { callbackUrl, error in
                if let callbackUrl {
                    continuation.resume(returning: callbackUrl)
                } else if (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin {
                    continuation.resume(returning: nil)
                } else {
                    continuation.resume(throwing: ImaginaFailure.unexpected)
                }
            }
            let session: ASWebAuthenticationSession
            if #available(iOS 17.4, *) {
                session = ASWebAuthenticationSession(url: url, callback: .customScheme(ImaginaParameters.applicationId), completionHandler: completion)
            } else {
                session = ASWebAuthenticationSession(url: url, callbackURLScheme: ImaginaParameters.applicationId, completionHandler: completion)
            }
            // A fresh browser session: no «wants to use … to sign in» alert, and every device signs in on its own.
            session.prefersEphemeralWebBrowserSession = true
            session.presentationContextProvider = self
            self.session = session
            if !session.start() {
                continuation.resume(throwing: ImaginaFailure.unexpected)
            }
        }
    }

    // MARK: PKCE

    private static var redirectUri: String { "\(ImaginaParameters.applicationId)://oauth2redirect" }

    private static func randomToken() -> String {
        var bytes = [UInt8](repeating: 0, count: 48)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return base64Url(Data(bytes))
    }

    private static func challenge(of verifier: String) -> String {
        base64Url(Data(SHA256.hash(data: Data(verifier.utf8))))
    }

    private static func base64Url(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

extension ImaginaAuthorization: ASWebAuthenticationPresentationContextProviding {
    nonisolated func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        MainActor.assumeIsolated {
            window ?? ASPresentationAnchor()
        }
    }
}
