// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import AuthenticationServices
import CryptoKit
import UIKit

/// «Entrar con Imagina»: instead of Nextcloud's server address and login pages, the person signs in with Imagina
/// (mobile number and SMS code) in a web sheet that closes by itself, and Imagina hands the app the Nextcloud
/// credentials of this device. Off unless `IMAGINA_AUTH_HOST` is set in imagina/imagina.properties.
///
/// OAuth 2.0 authorization code with PKCE against Imagina's OIDC server, public client.
@MainActor
final class ImaginaSignIn: NSObject {
    struct Credentials {
        let server: String
        let user: String
        let appPassword: String
    }

    static var isEnabled: Bool { !ImaginaParameters.authHost.isEmpty }

    private weak var screen: UIViewController?
    private let onSignedIn: (Credentials) async -> Void
    private var session: ASWebAuthenticationSession?
    private var button: UIButton?

    private init(screen: UIViewController, onSignedIn: @escaping (Credentials) async -> Void) {
        self.screen = screen
        self.onSignedIn = onSignedIn
    }

    /// Puts the «Entrar con Imagina» button on Nextcloud's login screen in place of the server address.
    /// The button keeps this object alive through its action.
    static func install(on screen: UIViewController, hiding views: [UIView?], onSignedIn: @escaping (Credentials) async -> Void) {
        let signIn = ImaginaSignIn(screen: screen, onSignedIn: onSignedIn)
        views.forEach { $0?.isHidden = true }

        var configuration = UIButton.Configuration.filled()
        configuration.title = ImaginaText.signIn
        configuration.baseBackgroundColor = ImaginaColor.ivory
        configuration.baseForegroundColor = ImaginaColor.ink
        configuration.cornerStyle = .large
        configuration.buttonSize = .large
        configuration.titleTextAttributesTransformer = UIConfigurationTextAttributesTransformer { incoming in
            var outgoing = incoming
            outgoing.font = UIFont.systemFont(ofSize: 17, weight: .semibold)
            return outgoing
        }

        let button = UIButton(configuration: configuration, primaryAction: UIAction { _ in signIn.start() })
        button.accessibilityIdentifier = "imaginaSignIn"
        button.translatesAutoresizingMaskIntoConstraints = false

        let hint = UILabel()
        hint.text = ImaginaText.signInHint
        hint.font = UIFont.preferredFont(forTextStyle: .footnote)
        hint.textColor = ImaginaColor.ivory.withAlphaComponent(0.85)
        hint.textAlignment = .center
        hint.numberOfLines = 0
        hint.translatesAutoresizingMaskIntoConstraints = false

        screen.view.addSubview(button)
        screen.view.addSubview(hint)
        NSLayoutConstraint.activate([
            button.centerXAnchor.constraint(equalTo: screen.view.centerXAnchor),
            button.centerYAnchor.constraint(equalTo: screen.view.centerYAnchor, constant: 40),
            button.widthAnchor.constraint(equalToConstant: 300),
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: 50),
            hint.topAnchor.constraint(equalTo: button.bottomAnchor, constant: 12),
            hint.centerXAnchor.constraint(equalTo: button.centerXAnchor),
            hint.widthAnchor.constraint(equalTo: button.widthAnchor)
        ])
        signIn.button = button
    }

    // MARK: - Sign-in

    private func start() {
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
            URLQueryItem(name: "scope", value: "openid profile email"),
            URLQueryItem(name: "state", value: state),
            URLQueryItem(name: "code_challenge", value: Self.challenge(of: verifier)),
            URLQueryItem(name: "code_challenge_method", value: "S256")
        ]
        guard let url = components.url else { return }

        let completion: ASWebAuthenticationSession.CompletionHandler = { [weak self] callbackUrl, _ in
            Task { @MainActor in
                await self?.finish(callbackUrl: callbackUrl, state: state, verifier: verifier)
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
        setBusy(true)
        if !session.start() {
            setBusy(false)
        }
    }

    private func finish(callbackUrl: URL?, state: String, verifier: String) async {
        session = nil
        defer { setBusy(false) }

        // Cancelled by the person: back to the button, without an error.
        guard let callbackUrl,
              let items = URLComponents(url: callbackUrl, resolvingAgainstBaseURL: false)?.queryItems else {
            return
        }
        guard items.first(where: { $0.name == "state" })?.value == state,
              let code = items.first(where: { $0.name == "code" })?.value,
              let credentials = await Self.credentials(code: code, verifier: verifier) else {
            showFailure()
            return
        }
        await onSignedIn(credentials)
    }

    /// Exchanges the code for a token and gets this device's Nextcloud credentials.
    ///
    /// Prototype (docs/PLAN_CLOUD.md, C0.12): Imagina's devices API (C7.1) will create a Nextcloud app password for
    /// this device with the token. Until then the token is checked against Imagina and the credentials come from
    /// imagina/imagina.local.properties.
    private static func credentials(code: String, verifier: String) async -> Credentials? {
        guard let token = await accessToken(code: code, verifier: verifier),
              let userInfoUrl = URL(string: "https://\(ImaginaParameters.authHost)/oauth/userinfo") else {
            return nil
        }
        var request = URLRequest(url: userInfoUrl, timeoutInterval: 20)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (_, response) = try? await URLSession.shared.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200 else {
            return nil
        }
        return Credentials(server: ImaginaParameters.cloudUrl,
                           user: ImaginaParameters.testNextcloudUser,
                           appPassword: ImaginaParameters.testNextcloudAppPassword)
    }

    private static func accessToken(code: String, verifier: String) async -> String? {
        guard let tokenUrl = URL(string: "https://\(ImaginaParameters.authHost)/oauth/token") else { return nil }
        var form = URLComponents()
        form.queryItems = [
            URLQueryItem(name: "grant_type", value: "authorization_code"),
            URLQueryItem(name: "client_id", value: ImaginaParameters.oauthClientId),
            URLQueryItem(name: "redirect_uri", value: redirectUri),
            URLQueryItem(name: "code", value: code),
            URLQueryItem(name: "code_verifier", value: verifier)
        ]
        var request = URLRequest(url: tokenUrl, timeoutInterval: 20)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        // URLComponents leaves «+» unescaped, which a form body reads as a space.
        request.httpBody = form.percentEncodedQuery?.replacingOccurrences(of: "+", with: "%2B").data(using: .utf8)

        guard let (data, response) = try? await URLSession.shared.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200,
              let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let token = body["access_token"] as? String, !token.isEmpty else {
            return nil
        }
        return token
    }

    // MARK: - Screen

    private func setBusy(_ busy: Bool) {
        button?.configuration?.showsActivityIndicator = busy
        button?.isEnabled = !busy
    }

    private func showFailure() {
        let alert = UIAlertController(title: ImaginaText.signInFailedTitle, message: ImaginaText.signInFailed, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: ImaginaText.ok, style: .default))
        screen?.present(alert, animated: true)
    }

    // MARK: - PKCE

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

extension ImaginaSignIn: ASWebAuthenticationPresentationContextProviding {
    nonisolated func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        MainActor.assumeIsolated {
            screen?.view.window ?? ASPresentationAnchor()
        }
    }
}
